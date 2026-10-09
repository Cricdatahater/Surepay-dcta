# Threat model

## Trust boundary

The LLM is an untrusted interpreter. It cannot access payment credentials, mutate
the frozen transaction, call execution directly, or treat earlier chat text as
authorization. Only the transaction kernel can create an executable command.

| Threat | Failure mode | Control |
|---|---|---|
| Ambiguous entity | Wrong “Alex” is paid | Never guess; resolve stable recipient ID or ask |
| Prompt injection | Message asks model to bypass policy | Model has no execution capability; kernel revalidates |
| Amount mutation | $80 becomes $800 | Integer money type, frozen summary, signed fingerprint |
| Approval replay | Same approval pays twice | Single-use token + idempotency key |
| UI race/double tap | Duplicate payment | Disable action and enforce server-side idempotency |
| Stale approval | Details change after review | Reject fingerprint mismatch and restart flow |
| Account draining | Scam empties balance | Risk threshold, cooling hold, step-up/manual route |
| Sensitive data leak | PII enters model logs | Minimise/tokenise context; redact logs; short retention |
| Model outage | Half-created payment | Fail closed; durable state machine; no execution on timeout |
| Social pressure | User is coached by scammer | Contextual pause/warning; preserve user agency; escalate |

## State transitions

Only these transitions are legal:

```text
draft → needs_clarification → draft
draft → blocked
draft → awaiting_authorization → declined
draft → awaiting_authorization → executed
```

There is deliberately no `conversation → executed` transition.

