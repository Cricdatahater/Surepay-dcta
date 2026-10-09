import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from dataclasses import replace
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from .domain import ActionType, Decision, Status, TransactionAction
from .intent_adapter import IntentAdapter
from .parser import ParsedAction, extract_audit_facts

ACCOUNTS = {"savings": "Savings • 2481", "current": "Current • 9032", "joint": "Joint Account • 7714", "investment": "Investment • 1840"}
RECIPIENTS = {
    "maya": [("r_maya_01", "Maya Tan", "•• 3401")], "maya tan": [("r_maya_01", "Maya Tan", "•• 3401")],
    "mom": [("r_mom_01", "Mei Lin", "•• 1188")], "mei lin": [("r_mom_01", "Mei Lin", "•• 1188")],
    "acme": [("r_acme_01", "ACME Pte. Ltd.", "•• 5019")], "acme pte ltd": [("r_acme_01", "ACME Pte. Ltd.", "•• 5019")],
    "alex": [("r_alex_01", "Alex Lim", "•• 6172")], "alex lim": [("r_alex_01", "Alex Lim", "•• 6172")],
    "john": [("r_john_d", "John Doe", "•• 4521"), ("r_john_s", "John Smith", "•• 8892")],
    "john doe": [("r_john_d", "John Doe", "•• 4521")], "john smith": [("r_john_s", "John Smith", "•• 8892")],
    "electricity": [("b_sp_01", "SP Services", "Utility bill")], "sp services": [("b_sp_01", "SP Services", "Utility bill")],
}
ASSETS = {"apple": "AAPL", "aapl": "AAPL", "dbs": "D05.SI", "tesla": "TSLA"}
MOCK_ASSET_PRICES = {"AAPL": 31_000, "D05.SI": 5_800, "TSLA": 62_000}
INJECTION_MARKERS = ("ignore all previous", "ignore previous instructions", "system prompt", "bypass authorization", "skip biometric", "developer message")
PIN_THRESHOLD = 10_000_00
OUT_OF_BAND_THRESHOLD = 50_000_00
AUTHORIZATION_TTL_SECONDS = 300
MOCK_KYC_REFERENCE = "SUREPAY-DEMO-2026"


class TransactionEngine:
    """Zero-trust kernel: conversational output is data, never authority."""

    def __init__(self, recipient_store: Path | None = None, intent_adapter: IntentAdapter | None = None) -> None:
        self.pending: dict[str, dict] = {}
        self.clarifications: dict[str, dict] = {}
        self.audit: dict[str, list[dict]] = {}
        self.executed: set[str] = set()
        self.recent_execution_times: list[float] = []
        self.sessions: dict[str, dict] = {}
        self.intent_adapter = intent_adapter or IntentAdapter()
        self._execution_lock = threading.RLock()
        self._mock_device_key = secrets.token_bytes(32)
        self._recipient_store = recipient_store
        self.recipients = {key: list(values) for key, values in RECIPIENTS.items()}
        self._load_recipients()
        self.balances = {
            ACCOUNTS["savings"]: 25_000_000,      # SGD 250,000.00
            ACCOUNTS["current"]: 8_000_000,       # SGD 80,000.00
            ACCOUNTS["joint"]: 12_000_000,        # SGD 120,000.00
            ACCOUNTS["investment"]: 15_000_000,   # SGD 150,000.00
        }

    def propose(self, text: str, conversation_id: str | None = None,
                session_id: str | None = None) -> Decision:
        clarification = self.clarifications.get(conversation_id or "")
        audit_id = clarification["audit_id"] if clarification else "AUD-" + secrets.token_hex(5).upper()
        if not clarification:
            self.audit[audit_id] = []
        self._log(audit_id, "input_received", {"raw_text": text, "channel": "text_or_voice"})
        if not self._session_has_verified_kyc(session_id):
            self._log(audit_id, "kyc_gate", {"result": "blocked"})
            return Decision(Status.KYC_REQUIRED,
                            "Complete mock KYC verification in the secure session before creating a transaction draft.",
                            risk_level="high", reasons=["KYC verification is incomplete"], audit_id=audit_id)
        self._log(audit_id, "kyc_gate", {"result": "verified"})
        if conversation_id and conversation_id in self.clarifications:
            return self._resolve_clarification(text, conversation_id, session_id)
        if self._is_balance_query(text):
            self._log(audit_id, "balance_query_redirected", {"result": "pin_required"})
            return Decision(Status.REQUIRES_PIN,
                            "Balance information is protected. Enter your session PIN in the secure balance screen.",
                            audit_id=audit_id)
        if any(marker in text.lower() for marker in INJECTION_MARKERS):
            self._log(audit_id, "semantic_firewall", {"result": "blocked"})
            return Decision(Status.BLOCKED, "I detected instructions attempting to bypass safeguards. Nothing was created.",
                            risk_level="high", reasons=["Semantic firewall triggered"], audit_id=audit_id)
        extraction = self.intent_adapter.extract(text)
        parsed = extraction.actions
        self._log(audit_id, "intent_extraction", {
            "provider": extraction.provider,
            "fallback_reason": extraction.fallback_reason,
            "action_count": len(parsed),
        })
        if not parsed or not any(a.amount_text or a.quantity_text for a in parsed):
            return Decision(Status.NEEDS_CLARIFICATION, "What amount or number of shares should I use? No transaction has been created.",
                            reasons=["Required transaction details are incomplete"], audit_id=audit_id)
        self._log(audit_id, "intent_draft", {"drafts": [a.__dict__ for a in parsed]})
        return self._compile(text, parsed, audit_id, session_id=session_id)

    def _compile(self, raw_text: str, parsed: list[ParsedAction], audit_id: str,
                 forced_recipient: tuple[str, str, str] | None = None,
                 session_id: str | None = None) -> Decision:
        actions: list[TransactionAction] = []
        for index, item in enumerate(parsed):
            source = ACCOUNTS.get(item.source_hint or ("investment" if item.kind == "investment" else "savings"))
            if item.kind == "investment":
                asset = ASSETS.get((item.asset_text or "").lower())
                quantity = int(item.quantity_text) if item.quantity_text else None
                amount = None if quantity else self._to_cents(item.amount_text or "")
                if not asset or (not quantity and amount <= 0):
                    return Decision(Status.NEEDS_CLARIFICATION,
                                    "Which supported asset and how much should I buy? Try ‘buy $500 of Apple’ or ‘buy 2 Apple shares’.",
                                    audit_id=audit_id)
                estimated_cost = MOCK_ASSET_PRICES[asset] * quantity if quantity else None
                actions.append(TransactionAction(ActionType.INVESTMENT, source, amount=amount,
                                                 asset_symbol=asset, quantity=quantity, estimated_cost=estimated_cost,
                                                 purpose="Equity purchase by quantity" if quantity else "Equity purchase by value"))
                continue
            if not item.amount_text or not item.recipient_text:
                return Decision(Status.NEEDS_CLARIFICATION, "I still need both the amount and recipient. No transaction has been created.", audit_id=audit_id)
            cents = self._to_cents(item.amount_text)
            if cents <= 0:
                return Decision(Status.BLOCKED, "The amount must be greater than zero.", audit_id=audit_id)
            matches = self.recipients.get(self._recipient_key(item.recipient_text), [])
            if forced_recipient and index == 0:
                matches = [forced_recipient]
            if len(matches) > 1:
                conversation_id = secrets.token_urlsafe(12)
                choices = [{"value": m[0], "label": f"{m[1]} {m[2]}"} for m in matches]
                self.clarifications[conversation_id] = {"raw": raw_text, "parsed": parsed, "audit_id": audit_id,
                                                        "matches": matches, "choices": choices,
                                                        "session_id": session_id}
                self._log(audit_id, "ambiguity_detected", {"field": "recipient", "choices": choices})
                return Decision(Status.NEEDS_CLARIFICATION,
                                f"I found {len(matches)} saved payees named {item.recipient_text}. Please provide the correct full name.",
                                conversation_id=conversation_id, choices=choices, audit_id=audit_id,
                                reasons=["Ambiguous beneficiary; no default selected"])
            if not matches:
                return Decision(Status.NEEDS_CLARIFICATION, f"I couldn't verify ‘{item.recipient_text}’ in your saved payees. Nothing was created.",
                                risk_level="high", reasons=["Unknown beneficiary"], audit_id=audit_id)
            match = matches[0]
            kind = ActionType.BILL_PAYMENT if item.kind == "bill_payment" else ActionType.TRANSFER
            actions.append(TransactionAction(kind, source, amount=cents, recipient_id=match[0],
                                             recipient_name=f"{match[1]} {match[2]}", purpose=item.purpose[:80]))

        actions, balance_error = self._project_balances(actions)
        if balance_error:
            self._log(audit_id, "balance_check", {"result": "blocked", "reason": balance_error})
            return Decision(Status.BLOCKED, balance_error, actions, "high",
                            ["Insufficient available balance"], audit_id=audit_id)
        validation = self._validate_independently(raw_text, actions)
        self._log(audit_id, "validation_agent", validation)
        if not validation["passed"]:
            return Decision(Status.BLOCKED, "The validation engine found a transcript/draft mismatch. The transaction is frozen.",
                            actions, "high", validation["discrepancies"], audit_id=audit_id, validation=validation)
        total = sum(a.amount if a.amount is not None else (a.estimated_cost or 0) for a in actions)
        if total > 100_000_00:
            return Decision(Status.BLOCKED, "This request exceeds the conversational limit. Use the secure banking flow.",
                            actions, "high", ["Batch exceeds SGD 100,000 limit"], audit_id=audit_id, validation=validation)
        self._prune_velocity()
        if len(self.recent_execution_times) >= 3:
            return Decision(Status.BLOCKED, "Velocity control paused conversational transactions. Please wait or use secure banking.",
                            actions, "high", ["Three recent transactions detected"], audit_id=audit_id, validation=validation)
        risk, reasons = self._risk(actions)
        authorization_id = secrets.token_urlsafe(18)
        fingerprint = self._fingerprint(actions)
        self.pending[authorization_id] = {"actions": actions, "fingerprint": fingerprint, "used": False,
                                          "audit_id": audit_id, "risk": risk, "total_debit": total,
                                          "created": time.time()}
        self._log(audit_id, "policy_gateway", {"result": "draft_only", "risk": risk, "fingerprint": fingerprint})
        return Decision(Status.AWAITING_AUTHORIZATION, "Validation passed. Review every detail; biometric approval signs this exact draft.",
                        actions, risk, reasons, authorization_id, audit_id=audit_id, validation=validation)

    def _resolve_clarification(self, selected_id: str, conversation_id: str,
                               session_id: str | None) -> Decision:
        state = self.clarifications[conversation_id]
        if state["session_id"] != session_id:
            return Decision(Status.BLOCKED, "This clarification belongs to a different secure session.",
                            risk_level="high", reasons=["Session binding mismatch"], audit_id=state["audit_id"])
        answer = selected_id.lower().strip()
        match = next((entry for entry in state["matches"]
                      if entry[0].lower() == answer or entry[1].lower() == answer), None)
        if not match:
            return Decision(Status.NEEDS_CLARIFICATION,
                            "That does not match the saved payees. Please enter the full name or select one below.",
                            risk_level="high", conversation_id=conversation_id, choices=state["choices"],
                            audit_id=state["audit_id"], reasons=["Ambiguity remains unresolved"])
        self.clarifications.pop(conversation_id)
        self._log(state["audit_id"], "ambiguity_resolved", {"recipient_id": match[0]})
        return self._compile(state["raw"], state["parsed"], state["audit_id"], match, session_id)

    def mock_biometric_sign(self, authorization_id: str) -> dict:
        with self._execution_lock:
            record = self.pending.get(authorization_id)
            if not self._authorization_is_active(record):
                self._expire_authorization(record)
                return {"ok": False, "error": "Authorization is invalid or expired"}
            payload = f"{authorization_id}:{record['fingerprint']}".encode()
            signature = hmac.new(self._mock_device_key, payload, hashlib.sha256).hexdigest()
            self._log(record["audit_id"], "mock_biometric", {"result": "verified", "signature": signature})
            return {"ok": True, "signature": signature, "method": "Mock biometric / device-bound HMAC",
                    "pin_required": record["total_debit"] >= PIN_THRESHOLD,
                    "out_of_band_required": record["total_debit"] >= OUT_OF_BAND_THRESHOLD}

    def authorize(self, authorization_id: str, approved: bool, signature: str | None = None,
                  step_up_token: str | None = None) -> Decision:
        with self._execution_lock:
            return self._authorize_locked(authorization_id, approved, signature, step_up_token)

    def _authorize_locked(self, authorization_id: str, approved: bool, signature: str | None = None,
                          step_up_token: str | None = None) -> Decision:
        record = self.pending.get(authorization_id)
        if not self._authorization_is_active(record):
            self._expire_authorization(record)
            return Decision(Status.BLOCKED, "This authorization is invalid, expired, or already used.", risk_level="high",
                            reasons=["Authorization expiry or replay protection triggered"])
        actions, audit_id = record["actions"], record["audit_id"]
        if not approved:
            record["used"] = True
            self._log(audit_id, "authorization", {"result": "declined"})
            return Decision(Status.DECLINED, "Transaction cancelled. No money moved.", actions, audit_id=audit_id)
        payload = f"{authorization_id}:{record['fingerprint']}".encode()
        expected = hmac.new(self._mock_device_key, payload, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            return Decision(Status.BLOCKED, "The API gateway rejected the request: no valid device signature.", actions, "high",
                            ["Cryptographic signature missing or invalid"], audit_id=audit_id)
        if record["total_debit"] >= PIN_THRESHOLD:
            expected_step_up = record.get("step_up_token")
            if not step_up_token or not expected_step_up or not hmac.compare_digest(step_up_token, expected_step_up):
                return Decision(Status.BLOCKED, "A valid transaction PIN step-up is required for this payment.", actions, "high",
                                ["Step-up authorization required"], audit_id=audit_id)
        if self._fingerprint(actions) != record["fingerprint"]:
            return Decision(Status.BLOCKED, "Transaction details changed after review. Start again.", actions, "high",
                            ["Authorization binding mismatch"], audit_id=audit_id)
        working_balances = dict(self.balances)
        for action in actions:
            if working_balances.get(action.source_account) != action.balance_before:
                return Decision(Status.BLOCKED, "The account balance changed after review. Please create a fresh draft.",
                                actions, "high", ["Stale balance projection"], audit_id=audit_id,
                                balances=self.public_balances())
            working_balances[action.source_account] = action.balance_after
        record["used"] = True
        record.pop("step_up_token", None)
        self.balances = working_balances
        transaction_id = "DCTA-" + secrets.token_hex(4).upper()
        self.executed.add(transaction_id)
        self.recent_execution_times.append(time.time())
        self._log(audit_id, "execution_gateway", {"result": "executed", "reference": transaction_id})
        return Decision(Status.EXECUTED, f"{len(actions)} action(s) complete. Reference {transaction_id}.", actions,
                        reasons=["Biometric signature verified", "Idempotency key consumed"], audit_id=audit_id,
                        balances=self.public_balances())

    def get_audit(self, audit_id: str) -> list[dict] | None:
        return self.audit.get(audit_id)

    def intent_status(self) -> dict:
        return self.intent_adapter.status()

    def start_session(self, pin: str) -> tuple[dict | None, str | None]:
        if not re.fullmatch(r"\d{6}", pin):
            return None, "The demo transaction PIN must contain exactly six digits."
        session_id = secrets.token_urlsafe(24)
        salt = secrets.token_bytes(16)
        pin_hash = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 200_000)
        self.sessions[session_id] = {"salt": salt, "pin_hash": pin_hash, "attempts": 0,
                                    "locked_until": 0.0, "created": time.time(),
                                    "kyc_status": "pending", "kyc_verified_at": None}
        return {"session_id": session_id, "pin_threshold": PIN_THRESHOLD,
                "out_of_band_threshold": OUT_OF_BAND_THRESHOLD, "kyc_status": "pending"}, None

    def verify_mock_kyc(self, session_id: str, demo_reference: str) -> dict:
        session = self.sessions.get(session_id)
        if not session:
            return {"ok": False, "status": "unavailable",
                    "error": "The secure session is invalid. Reload and create a new session PIN."}
        if not hmac.compare_digest(demo_reference.strip().upper(), MOCK_KYC_REFERENCE):
            return {"ok": False, "status": session["kyc_status"],
                    "error": "Mock KYC verification failed. Check the demo customer reference and try again."}
        session["kyc_status"] = "verified"
        session["kyc_verified_at"] = time.time()
        return {"ok": True, "status": "verified", "message": "Mock KYC verification complete."}

    def _session_has_verified_kyc(self, session_id: str | None) -> bool:
        session = self.sessions.get(session_id or "")
        return bool(session and session["kyc_status"] == "verified")

    def verify_step_up(self, authorization_id: str, session_id: str, pin: str,
                       out_of_band_confirmed: bool) -> dict:
        with self._execution_lock:
            record = self.pending.get(authorization_id)
            if not self._authorization_is_active(record):
                self._expire_authorization(record)
                return {"ok": False, "error": "The transaction authorization is invalid or expired."}
            verified, error = self._verify_session_pin(session_id, pin)
            if not verified:
                self._log(record["audit_id"], "pin_step_up", {"result": "failed"})
                return {"ok": False, "error": error}
            if record["total_debit"] >= OUT_OF_BAND_THRESHOLD and not out_of_band_confirmed:
                return {"ok": False, "error": "Confirm approval on the registered-device simulation for this high-value payment."}
            token = secrets.token_urlsafe(24)
            record["step_up_token"] = token
            self._log(record["audit_id"], "pin_step_up",
                      {"result": "verified", "out_of_band": record["total_debit"] >= OUT_OF_BAND_THRESHOLD})
            return {"ok": True, "step_up_token": token}

    def secure_balance_query(self, session_id: str, pin: str, query: str) -> dict:
        if not self._is_balance_query(query):
            return {"ok": False, "error": "The request is not a recognised balance enquiry."}
        verified, error = self._verify_session_pin(session_id, pin)
        if not verified:
            return {"ok": False, "error": error}
        return {"ok": True, "message": "PIN verified. Here are your current mock balances.",
                "balances": self._balances_for_query(query)}

    def _verify_session_pin(self, session_id: str, pin: str) -> tuple[bool, str | None]:
        session = self.sessions.get(session_id)
        if not session:
            return False, "The secure session is invalid. Reload and create a new session PIN."
        now = time.time()
        if session["locked_until"] > now:
            wait = max(1, int(session["locked_until"] - now))
            return False, f"PIN verification is temporarily locked. Try again in {wait} seconds."
        candidate = hashlib.pbkdf2_hmac("sha256", pin.encode(), session["salt"], 200_000)
        if not hmac.compare_digest(candidate, session["pin_hash"]):
            session["attempts"] += 1
            if session["attempts"] >= 3:
                session["locked_until"] = now + 30
                session["attempts"] = 0
            return False, "Incorrect transaction PIN."
        session["attempts"] = 0
        return True, None

    def public_recipients(self) -> list[dict[str, object]]:
        unique: dict[str, dict[str, object]] = {}
        for matches in self.recipients.values():
            for recipient_id, name, detail in matches:
                # Never show a payee unless its displayed full name resolves back
                # to the same stable server-side recipient ID.
                canonical_matches = self.recipients.get(self._recipient_key(name), [])
                if any(match[0] == recipient_id for match in canonical_matches):
                    unique[recipient_id] = {"id": recipient_id, "name": name, "detail": detail, "verified": True}
        return sorted(unique.values(), key=lambda item: (item["name"].lower(), item["detail"]))

    def add_recipient(self, name: str, bank: str, account_last4: str) -> tuple[dict | None, str | None]:
        clean_name = " ".join(name.strip().split())
        clean_bank = " ".join(bank.strip().split())
        if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,49}", clean_name):
            return None, "Enter a valid recipient name using letters, spaces, apostrophes, periods, or hyphens."
        allowed_banks = {"DBS", "POSB", "OCBC", "UOB", "Standard Chartered"}
        if clean_bank not in allowed_banks:
            return None, "Select a supported bank."
        if not re.fullmatch(r"\d{4}", account_last4):
            return None, "Account ending must contain exactly four digits."
        key = self._recipient_key(clean_name)
        detail = f"{clean_bank} •• {account_last4}"
        if any(existing[2].endswith(account_last4) for existing in self.recipients.get(key, [])):
            return None, "That recipient and account ending already exist."
        recipient = ("r_custom_" + secrets.token_hex(5), clean_name, detail)
        self.recipients.setdefault(key, []).append(recipient)
        self._persist_recipients()
        return {"id": recipient[0], "name": recipient[1], "detail": recipient[2]}, None

    @staticmethod
    def _recipient_key(name: str) -> str:
        return " ".join(name.lower().replace(".", "").split())

    def _load_recipients(self) -> None:
        if not self._recipient_store or not self._recipient_store.exists():
            return
        try:
            stored = json.loads(self._recipient_store.read_text(encoding="utf-8"))
            for item in stored:
                key = self._recipient_key(item["name"])
                entry = (item["id"], item["name"], item["detail"])
                if not any(existing[0] == entry[0] for existing in self.recipients.get(key, [])):
                    self.recipients.setdefault(key, []).append(entry)
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            # A corrupt optional demo store must not weaken transaction safety.
            pass

    def _persist_recipients(self) -> None:
        if not self._recipient_store:
            return
        custom = [item for item in self.public_recipients() if item["id"].startswith("r_custom_")]
        self._recipient_store.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._recipient_store.with_suffix(".tmp")
        temporary.write_text(json.dumps(custom, indent=2), encoding="utf-8")
        temporary.replace(self._recipient_store)

    def public_balances(self, actions: list[TransactionAction] | None = None) -> dict[str, str]:
        names = {a.source_account for a in actions} if actions else set(self.balances)
        return {name: f"SGD {self.balances[name] / 100:,.2f}" for name in self.balances if name in names}

    @staticmethod
    def _is_balance_query(text: str) -> bool:
        lowered = text.lower()
        return bool(re.search(r"\b(balance|balances|funds available|available funds|money left|remaining funds|remaining balance)\b", lowered))

    def _balances_for_query(self, text: str) -> dict[str, str]:
        lowered = text.lower()
        account_terms = {
            "savings": ACCOUNTS["savings"], "current": ACCOUNTS["current"],
            "joint": ACCOUNTS["joint"], "investment": ACCOUNTS["investment"],
        }
        selected = {account for term, account in account_terms.items() if term in lowered}
        if not selected:
            return self.public_balances()
        return {name: f"SGD {self.balances[name] / 100:,.2f}" for name in self.balances if name in selected}

    def _project_balances(self, actions: list[TransactionAction]) -> tuple[list[TransactionAction], str | None]:
        projected = dict(self.balances)
        enriched: list[TransactionAction] = []
        for action in actions:
            debit = action.amount if action.amount is not None else (action.estimated_cost or 0)
            before = projected[action.source_account]
            after = before - debit
            enriched_action = replace(action, balance_before=before, balance_after=after)
            enriched.append(enriched_action)
            if after < 0:
                return enriched, f"Insufficient funds in {action.source_account}. Available: SGD {before / 100:,.2f}."
            projected[action.source_account] = after
        return enriched, None

    @staticmethod
    def _to_cents(value: str) -> int:
        try:
            return int((Decimal(value.replace(",", "")) * 100).quantize(Decimal("1"), ROUND_HALF_UP))
        except (InvalidOperation, ValueError):
            return 0

    def _validate_independently(self, raw_text: str, actions: list[TransactionAction]) -> dict:
        facts = extract_audit_facts(raw_text)
        # Canonicalise both sides to integer cents. Display precision, trailing
        # zeros, and speech/parser formatting can never create a false mismatch.
        transcript_amounts = [
            int((Decimal(value) * 100).quantize(Decimal("1"), ROUND_HALF_UP))
            for value in facts["explicit_amounts"]
        ]
        action_amounts = [a.amount for a in actions if a.amount is not None]
        discrepancies = []
        if transcript_amounts and len(transcript_amounts) != len(action_amounts):
            discrepancies.append("Number of explicit amounts does not match the compiled draft")
        elif transcript_amounts:
            if transcript_amounts != action_amounts:
                discrepancies.append("An amount differs from the raw transcript")

        action_facts = facts["action_facts"]
        if len(action_facts) != len(actions):
            discrepancies.append("Action count differs from the raw transcript")
        for index, (fact, action) in enumerate(zip(action_facts, actions), start=1):
            expected_kind = "investment" if action.action_type == ActionType.INVESTMENT else "payment"
            if fact["kind"] != expected_kind:
                discrepancies.append(f"Action {index} type differs from the raw transcript")
            if fact["amount"] is not None:
                expected_amount = self._to_cents(fact["amount"])
                if action.amount != expected_amount:
                    discrepancies.append(f"Action {index} amount differs from the raw transcript")
            if fact["source"] and action.source_account != ACCOUNTS[fact["source"]]:
                discrepancies.append(f"Action {index} source account differs from the raw transcript")
            if fact["recipient"]:
                matches = self.recipients.get(self._recipient_key(fact["recipient"]), [])
                if not any(match[0] == action.recipient_id for match in matches):
                    discrepancies.append(f"Action {index} beneficiary differs from the raw transcript")
            if fact["asset"] and action.asset_symbol != ASSETS.get(fact["asset"]):
                discrepancies.append(f"Action {index} asset differs from the raw transcript")
            if fact["quantity"] is not None and action.quantity != fact["quantity"]:
                discrepancies.append(f"Action {index} quantity differs from the raw transcript")

        discrepancies = list(dict.fromkeys(discrepancies))
        return {"passed": not discrepancies, "engine": "independent read-only validator",
                "checks": ["amount", "beneficiary", "action count", "action type", "source account",
                           "asset", "quantity"], "discrepancies": discrepancies}

    @staticmethod
    def _authorization_is_active(record: dict | None) -> bool:
        return bool(record and not record["used"] and
                    time.time() - record["created"] <= AUTHORIZATION_TTL_SECONDS)

    def _expire_authorization(self, record: dict | None) -> None:
        if not record or record["used"]:
            return
        if time.time() - record["created"] > AUTHORIZATION_TTL_SECONDS:
            record["used"] = True
            record.pop("step_up_token", None)
            self._log(record["audit_id"], "authorization_expired",
                      {"ttl_seconds": AUTHORIZATION_TTL_SECONDS})

    @staticmethod
    def _risk(actions: list[TransactionAction]) -> tuple[str, list[str]]:
        total = sum(a.amount if a.amount is not None else (a.estimated_cost or 0) for a in actions)
        if total >= 50_000_00:
            return "high", ["Large-value request", "Out-of-band step-up required"]
        if len(actions) > 1 or total >= 2_000_00 or any(a.action_type == ActionType.INVESTMENT for a in actions):
            return "medium", ["Multi-action, investment, or above-usual-value request"]
        return "low", ["Verified payee", "Within conversational threshold"]

    @staticmethod
    def _fingerprint(actions: list[TransactionAction]) -> str:
        return hashlib.sha256(json.dumps([a.public_dict() for a in actions], sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    def _prune_velocity(self) -> None:
        cutoff = time.time() - 60
        self.recent_execution_times = [t for t in self.recent_execution_times if t >= cutoff]

    def _log(self, audit_id: str, event: str, details: dict) -> None:
        self.audit[audit_id].append({"at": time.time(), "event": event, "details": details})
