"""Untrusted conversational adapter; production swaps this for TokenHub output."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedAction:
    kind: str
    raw_segment: str
    amount_text: str | None = None
    recipient_text: str | None = None
    purpose: str = ""
    source_hint: str | None = None
    asset_text: str | None = None
    quantity_text: str | None = None


NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


def parse_number(text: str) -> str | None:
    numeric = re.search(r"(?:sgd|s\$|\$)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text, re.I)
    if numeric:
        return numeric.group(1)
    words = re.findall(r"\b(?:" + "|".join(NUMBER_WORDS) + r"|hundred|thousand|grand)\b", text.lower())
    if not words:
        return None
    total = current = 0
    for word in words:
        if word in NUMBER_WORDS:
            current += NUMBER_WORDS[word]
        elif word == "hundred":
            current = max(current, 1) * 100
        elif word in {"thousand", "grand"}:
            total += max(current, 1) * 1000
            current = 0
    return str(total + current)


def parse_actions(text: str) -> list[ParsedAction]:
    segments = split_action_segments(text)
    actions: list[ParsedAction] = []
    for segment in segments:
        lower = segment.lower()
        source = re.search(r"\bfrom\s+(?:my\s+)?(savings|current|joint|investment)(?:\s+account)?", segment, re.I)
        source_hint = source.group(1).lower() if source else None
        if re.search(r"\b(?:buy|invest)\b", lower):
            order = (re.search(r"\b(?:buy|purchase)\s+([0-9]+)\s+([A-Za-z]{2,15})(?:\s+shares?)?", segment, re.I)
                     or re.search(r"\b(?:buy|purchase)\s+([0-9]+)\s+shares?\s+of\s+([A-Za-z]{2,15})", segment, re.I))
            by_value = re.search(r"\b(?:buy|invest)\s+.+?\s+(?:of|in)\s+([A-Za-z]{2,15})(?:\s+shares?)?\b", segment, re.I)
            actions.append(ParsedAction("investment", segment, parse_number(segment), source_hint=source_hint,
                                        asset_text=order.group(2) if order else (by_value.group(1) if by_value else None),
                                        quantity_text=order.group(1) if order else None))
            continue
        recipient = re.search(r"\b(?:to|pay)\s+(?:my\s+)?([A-Za-z][A-Za-z0-9 &.'-]{0,40}?)(?=,|\s+(?:for|from|using)\b|$)", segment, re.I)
        purpose = re.search(r"\bfor\s+(.+?)(?=\s+from\b|$)", segment, re.I)
        kind = "bill_payment" if "bill" in lower or lower.startswith("pay my") else "transfer"
        actions.append(ParsedAction(kind, segment, parse_number(segment),
                                    recipient.group(1).strip() if recipient else None,
                                    purpose.group(1).strip() if purpose else "Personal transfer", source_hint))
    return actions


def split_action_segments(text: str) -> list[str]:
    normalized = " ".join(text.strip().split())
    return re.split(r"\s+(?:and then|then|and)\s+(?=(?:send|transfer|pay|buy|invest)\b)",
                    normalized, flags=re.I)


def extract_audit_facts(text: str) -> dict:
    """Independent read-only extraction for dual-engine discrepancy auditing."""
    money = re.findall(r"(?:sgd|s\$|\$)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", text, re.I)
    recipients = re.findall(r"\bto\s+(?:my\s+)?([A-Za-z][A-Za-z .'’-]*?)(?=\s+(?:for|from|and|then)\b|$)", text, re.I)
    action_facts = []
    for segment in split_action_segments(text):
        investment = bool(re.search(r"\b(?:buy|invest|purchase)\b", segment, re.I))
        source = re.search(r"\bfrom\s+(?:my\s+)?(savings|current|joint|investment)(?:\s+account)?\b",
                           segment, re.I)
        amount = re.search(r"(?:sgd|s\$|\$)\s*([0-9][0-9,]*(?:\.\d{1,2})?)", segment, re.I)
        recipient = None if investment else re.search(
            r"\b(?:to|pay)\s+(?:my\s+)?([A-Za-z][A-Za-z0-9 &.'-]{0,40}?)(?=,|\s+(?:for|from|using)\b|$)",
            segment, re.I,
        )
        order = None
        asset = None
        if investment:
            order = (re.search(r"\b(?:buy|purchase)\s+([0-9]+)\s+([A-Za-z]{2,15})(?:\s+shares?)?", segment, re.I)
                     or re.search(r"\b(?:buy|purchase)\s+([0-9]+)\s+shares?\s+of\s+([A-Za-z]{2,15})", segment, re.I))
            by_value = re.search(r"\b(?:buy|invest)\s+.+?\s+(?:of|in)\s+([A-Za-z]{2,15})(?:\s+shares?)?\b",
                                 segment, re.I)
            asset = order.group(2) if order else (by_value.group(1) if by_value else None)
        action_facts.append({
            "kind": "investment" if investment else "payment",
            "amount": amount.group(1).replace(",", "") if amount else None,
            "recipient": recipient.group(1).strip().lower() if recipient else None,
            "source": source.group(1).lower() if source else None,
            "asset": asset.lower() if asset else None,
            "quantity": int(order.group(1)) if order else None,
        })
    return {"explicit_amounts": [m.replace(",", "") for m in money],
            "explicit_recipients": [r.strip().lower() for r in recipients],
            "explicit_sources": [source.lower() for source in re.findall(
                r"\bfrom\s+(?:my\s+)?(savings|current|joint|investment)(?:\s+account)?\b", text, re.I
            )], "action_facts": action_facts,
            "action_verbs": re.findall(r"\b(send|transfer|pay|buy|invest)\b", text.lower())}
