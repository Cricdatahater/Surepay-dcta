import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dcta.engine import TransactionEngine


ROOT = Path(__file__).parent.resolve()
WEB = ROOT / "web"
ENGINE = TransactionEngine(ROOT / "data" / "recipients.json")
BUILD_VERSION = "20261004.1"


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = min(int(self.headers.get("Content-Length", "0")), 16_384)
        return json.loads(self.rfile.read(length) or b"{}")

    def do_POST(self) -> None:
        try:
            data = self._body()
            if self.path == "/api/chat":
                text = str(data.get("message", ""))[:500]
                conversation_id = data.get("conversation_id")
                session_id = str(data.get("session_id", ""))
                return self._json(200, ENGINE.propose(text, conversation_id, session_id).public_dict())
            if self.path == "/api/biometric":
                return self._json(200, ENGINE.mock_biometric_sign(str(data.get("authorization_id", ""))))
            if self.path == "/api/recipients":
                recipient, error = ENGINE.add_recipient(
                    str(data.get("name", "")), str(data.get("bank", "")), str(data.get("account_last4", ""))
                )
                return self._json(201 if recipient else 400, {"recipient": recipient, "error": error})
            if self.path == "/api/session/start":
                session, error = ENGINE.start_session(str(data.get("pin", "")))
                return self._json(201 if session else 400, {"session": session, "error": error})
            if self.path == "/api/kyc/verify":
                result = ENGINE.verify_mock_kyc(
                    str(data.get("session_id", "")), str(data.get("demo_reference", ""))
                )
                return self._json(200 if result.get("ok") else 400, result)
            if self.path == "/api/step-up":
                result = ENGINE.verify_step_up(
                    str(data.get("authorization_id", "")), str(data.get("session_id", "")),
                    str(data.get("pin", "")), data.get("out_of_band_confirmed") is True,
                )
                return self._json(200 if result.get("ok") else 400, result)
            if self.path == "/api/balance":
                result = ENGINE.secure_balance_query(
                    str(data.get("session_id", "")), str(data.get("pin", "")), str(data.get("query", ""))
                )
                return self._json(200 if result.get("ok") else 400, result)
            if self.path == "/api/authorize":
                result = ENGINE.authorize(
                    str(data.get("authorization_id", "")), data.get("approved") is True,
                    data.get("signature"), data.get("step_up_token"),
                )
                return self._json(200, result.public_dict())
            self._json(404, {"error": "Not found"})
        except (json.JSONDecodeError, TypeError, ValueError):
            self._json(400, {"error": "Invalid request"})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._json(200, {"status": "ok", "mode": "simulation", "build": BUILD_VERSION,
                                    "intent_engine": ENGINE.intent_status()})
        if path == "/api/recipients":
            return self._json(200, {"recipients": ENGINE.public_recipients()})
        if path.startswith("/api/audit/"):
            audit_id = path.removeprefix("/api/audit/")
            events = ENGINE.get_audit(audit_id)
            return self._json(200 if events is not None else 404, {"audit_id": audit_id, "events": events or []})
        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (WEB / relative).resolve()
        if WEB not in candidate.parents or not candidate.is_file():
            self.send_error(404)
            return
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(candidate)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[SurePay] {fmt % args}")


if __name__ == "__main__":
    host = os.environ.get("DCTA_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", os.environ.get("DCTA_PORT", "8000")))
    address = (host, port)
    print(f"SurePay simulation running at http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, Handler).serve_forever()
