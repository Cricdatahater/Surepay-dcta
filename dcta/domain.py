from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Status(str, Enum):
    INFORMATION = "information"
    KYC_REQUIRED = "kyc_required"
    REQUIRES_PIN = "requires_pin"
    DRAFT = "draft"
    NEEDS_CLARIFICATION = "needs_clarification"
    BLOCKED = "blocked"
    AWAITING_AUTHORIZATION = "awaiting_authorization"
    EXECUTED = "executed"
    DECLINED = "declined"


class ActionType(str, Enum):
    TRANSFER = "transfer"
    BILL_PAYMENT = "bill_payment"
    INVESTMENT = "investment"


@dataclass(frozen=True)
class TransactionAction:
    action_type: ActionType
    source_account: str
    currency: str = "SGD"
    amount: int | None = None
    recipient_id: str | None = None
    recipient_name: str | None = None
    purpose: str = ""
    asset_symbol: str | None = None
    quantity: int | None = None
    estimated_cost: int | None = None
    balance_before: int | None = None
    balance_after: int | None = None

    def public_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["action_type"] = self.action_type.value
        data["amount_display"] = f"{self.currency} {self.amount / 100:,.2f}" if self.amount is not None else None
        data["estimated_cost_display"] = f"{self.currency} {self.estimated_cost / 100:,.2f}" if self.estimated_cost is not None else None
        data["balance_before_display"] = f"{self.currency} {self.balance_before / 100:,.2f}" if self.balance_before is not None else None
        data["balance_after_display"] = f"{self.currency} {self.balance_after / 100:,.2f}" if self.balance_after is not None else None
        return data


TransferIntent = TransactionAction


@dataclass
class Decision:
    status: Status
    message: str
    actions: list[TransactionAction] = field(default_factory=list)
    risk_level: str = "low"
    reasons: list[str] = field(default_factory=list)
    authorization_id: str | None = None
    conversation_id: str | None = None
    choices: list[dict[str, str]] = field(default_factory=list)
    audit_id: str | None = None
    validation: dict[str, Any] = field(default_factory=dict)
    balances: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def intent(self) -> TransactionAction | None:
        return self.actions[0] if self.actions else None

    def public_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "intent": self.intent.public_dict() if self.intent else None,
            "actions": [a.public_dict() for a in self.actions],
            "risk_level": self.risk_level,
            "reasons": self.reasons,
            "authorization_id": self.authorization_id,
            "conversation_id": self.conversation_id,
            "choices": self.choices,
            "audit_id": self.audit_id,
            "validation": self.validation,
            "balances": self.balances,
            "created_at": self.created_at,
        }
