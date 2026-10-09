"""Intent extraction adapters. Model output is untrusted transaction input."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .parser import ParsedAction, parse_actions


TOKENHUB_DEFAULT_URL = "https://tokenhub-intl.tencentcloudmaas.com/v1/chat/completions"


@dataclass(frozen=True)
class IntentExtraction:
    actions: list[ParsedAction]
    provider: str
    fallback_reason: str | None = None


class IntentAdapter:
    """Use Tencent TokenHub when configured, with a deterministic offline fallback."""

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 endpoint: str | None = None, timeout_seconds: float = 8.0) -> None:
        self.api_key = api_key if api_key is not None else os.environ.get("TENCENT_TOKENHUB_API_KEY", "")
        self.model = model or os.environ.get("TENCENT_TOKENHUB_MODEL", "hy4-preview")
        self.endpoint = endpoint or os.environ.get("TENCENT_TOKENHUB_URL", TOKENHUB_DEFAULT_URL)
        self.timeout_seconds = timeout_seconds

    def status(self) -> dict[str, object]:
        return {
            "provider": "tencent_tokenhub" if self.api_key else "deterministic_local",
            "model": self.model if self.api_key else None,
            "configured": bool(self.api_key),
        }

    def extract(self, text: str) -> IntentExtraction:
        if not self.api_key:
            return IntentExtraction(parse_actions(text), "deterministic_local")
        try:
            return IntentExtraction(self._extract_with_tokenhub(text), "tencent_tokenhub")
        except (OSError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError,
                urllib.error.URLError):
            # Availability of an external model must never weaken or stop the
            # deterministic validation and authorization controls.
            return IntentExtraction(parse_actions(text), "deterministic_local", "tokenhub_unavailable_or_invalid")

    def _extract_with_tokenhub(self, text: str) -> list[ParsedAction]:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "actions": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "kind": {"type": "string", "enum": ["transfer", "bill_payment", "investment"]},
                            "raw_segment": {"type": "string"},
                            "amount_text": {"type": ["string", "null"]},
                            "recipient_text": {"type": ["string", "null"]},
                            "purpose": {"type": "string"},
                            "source_hint": {"type": ["string", "null"],
                                            "enum": ["savings", "current", "joint", "investment", None]},
                            "asset_text": {"type": ["string", "null"]},
                            "quantity_text": {"type": ["string", "null"]},
                        },
                        "required": ["kind", "raw_segment", "amount_text", "recipient_text", "purpose",
                                     "source_hint", "asset_text", "quantity_text"],
                    },
                }
            },
            "required": ["actions"],
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": (
                    "Extract only transaction actions explicitly requested by the customer. "
                    "Never infer a recipient, amount, account, asset, or quantity. Keep raw_segment as an exact "
                    "substring of the customer text. Use null for missing fields. Amount text must contain only "
                    "the stated numeric value without a currency symbol."
                )},
                {"role": "user", "content": text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "transaction_intents", "strict": True, "schema": schema},
            },
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                raise ValueError("TokenHub returned a non-success status")
            result = json.loads(response.read())
        content = result["choices"][0]["message"]["content"]
        document = json.loads(content)
        actions = []
        for item in document["actions"]:
            raw_segment = str(item["raw_segment"]).strip()
            if not raw_segment or raw_segment.lower() not in text.lower():
                raise ValueError("Model returned a segment that is not in the transcript")
            actions.append(ParsedAction(
                kind=item["kind"], raw_segment=raw_segment,
                amount_text=self._optional_text(item["amount_text"]),
                recipient_text=self._optional_text(item["recipient_text"]),
                purpose=str(item["purpose"])[:80],
                source_hint=item["source_hint"],
                asset_text=self._optional_text(item["asset_text"]),
                quantity_text=self._optional_text(item["quantity_text"]),
            ))
        return actions

    @staticmethod
    def _optional_text(value: object) -> str | None:
        return None if value is None else str(value).strip() or None
