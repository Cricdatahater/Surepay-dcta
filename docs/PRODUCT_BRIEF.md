# Product brief: SurePay

## Chosen challenge scenario

**DBS Scenario 1: Voice-Enabled Payment and Transaction.** SurePay demonstrates
voice initiation, mock KYC/risk controls, independent semantic auditing, and a
mock bank execution gateway. Scenario 2 is deliberately out of scope.

## One-line pitch

SurePay lets customers request a payment in natural language while a separate,
deterministic transaction kernel makes ambiguity, manipulation, and accidental
execution structurally incapable of moving money.

## Target user and job

Primary persona: a mobile-banking customer who wants the speed of conversation
without surrendering control. Their job is not “chat with a bank”; it is “pay the
right person, the right amount, once, with confidence.”

## Golden demo

1. Speak: “Send $80 to Maya for dinner and buy 2 Apple shares.” The draft engine
   constructs two structured actions.
2. A separate read-only validator compares the draft to the raw transcript.
3. The deterministic overlay shows every action and risk decision.
4. Mock FaceID signs the exact batch fingerprint; only then can the gateway run.
5. “Send fifty to John” triggers targeted disambiguation, and an injection or
   transcript discrepancy visibly freezes the transaction.

## Architecture

```text
Customer utterance
      │
      ▼
Voice STT / LLM draft adapter ──── no execution credentials
      │ typed, untrusted JSON
      ▼
Independent semantic validator → recipient resolution → KYC/risk/velocity policy
      │
      ▼
Native overlay + frozen batch fingerprint + mock biometric signature
      │ explicit transaction signing
      ▼
Zero-trust API gateway → mock bank service → receipt + complete audit trail
```

The prototype implements the full lifecycle with a deterministic local parser.
Tencent TokenHub structured output can replace only the intent adapter; the
transaction kernel remains model-independent.

## MVP acceptance criteria

- Never infer an unknown recipient.
- Never execute from conversational text alone.
- Amount is stored as integer cents, never floating point.
- Approval binds to exact source, recipient, amount, currency, and purpose.
- Authorization is single-use and replay-safe.
- Clear escalation/blocking for unsupported or high-risk requests.
- No sensitive account data is sent to the language model.

## Judging strategy

| Dimension | Evidence in submission |
|---|---|
| Relevance | Safe end-to-end conversational transfer demo |
| Human-centred | Plain-language recovery, exact review card, hold-to-approve |
| AI use | Multilingual structured intent + explanation, isolated from execution |
| Technical execution | Typed contract, policy kernel, idempotency, audit trail, tests |
| Feasibility | Adapter architecture and sandbox-ready payment interface |
| Responsible AI | No autonomous transfer, fail-closed ambiguity, prompt-injection boundary |
| Business impact | Lower payment friction without weakening authentication |

## Roadmap to 16 October

### Week 1 — brief and evidence

- Obtain the official DBS challenge deck, rubric, submission fields, sandbox/API
  availability, team-size rules, and mentor schedule.
- Interview 5–8 users on payment anxiety and ambiguous recipient scenarios.
- Freeze demo story and success metrics.

### Week 2 — safe vertical slice

- Connect Tencent TokenHub with JSON-schema output.
- Implement signed session, recipient directory, limits, risk rules, and audit log.
- Add PayNow/mobile-number and QR intent types in simulation.

### Week 3 — differentiation

- Add English/Mandarin/Singlish evaluation set.
- Add scam-pressure detection as a warning signal, never as sole authority.
- Build an adversarial suite: injection, amount mutation, recipient ambiguity,
  replay, double-click, stale authorization, and partial service failure.

### Week 4 — submission

- Deploy, instrument latency and task-completion metrics, record a 5–8 minute demo.
- Finish architecture diagram, responsible-AI statement, README, pitch deck.
- Run a timed pitch and failure-mode demo; submit at least 24 hours early.

## Metrics

- 100% block rate on unauthorized execution tests.
- 0 silent recipient guesses.
- ≥95% exact intent extraction on the curated test set.
- Median request-to-review latency <2 seconds.
- ≥90% users can identify recipient and amount before approval.
- 100% duplicate/replay requests return the original result or fail closed.
