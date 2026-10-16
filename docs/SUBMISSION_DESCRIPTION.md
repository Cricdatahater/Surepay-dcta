# SurePay — Direct Conversational Transaction Agent

**Track:** Banking — DBS  
**Selected case:** Scenario 1: Voice-Enabled Payment and Transaction  
**Short blurb:** Safe conversational banking with transaction-bound authorization.

## Project overview

SurePay is a conversational banking prototype that lets customers request transfers, bill payments, and equity purchases through text or browser-supported speech input. A customer can combine a transfer and an investment in one request, choose the payment account, review each action, and approve the exact transaction draft.

The target users are mobile-banking customers who want a simpler way to complete everyday financial tasks while retaining control over the recipient, source account, amount, and investment quantity. SurePay's value proposition is a single conversational entry point supported by explicit review and deterministic banking controls.

For example, “Send $80 to Maya from my current account and buy 2 Apple shares” produces a batch with a Current-account transfer and an Investment-account purchase. The customer sees both actions and their projected balances before approval. If a name matches multiple saved payees, SurePay asks which person the customer intended.

## Real-world scenario insights

The source of the problem is the DBS challenge statement, which identifies menu friction, unauthorized agent behavior, prompt injection, ambiguous speech, and the difficulty of proving consent in conversational transactions. SurePay translates those concerns into observable prototype behaviors.

Customers face repeated navigation when a task spans payments and investments. Names such as “John” can refer to multiple payees, and an incorrect amount or account can have a meaningful financial consequence. Introducing generative AI adds a further concern: an interpretation error should not itself become a money movement.

SurePay addresses these problems through combined drafts, automatic recipient clarification, an independent transcript check, and a separate approval step. Unknown payees are never silently guessed. Customers can add a mock recipient through a dedicated form, request balances through a PIN-protected flow, and choose the account for a payment.

These insights are grounded in the supplied challenge brief. Customer interviews and comparative user studies have not yet been completed; no user-research findings or adoption statistics are claimed.

## Comprehensive solution design

### Business workflow

1. The customer creates a six-digit demo PIN and completes a separate mock KYC ceremony.
2. The server checks session KYC before transaction intent extraction.
3. The customer types, dictates, or builds a request containing one or more actions.
4. Candidate actions are resolved against the mock account, payee, and asset metadata.
5. A read-only validator compares the compiled draft with transcript facts. A discrepancy blocks progression.
6. Deterministic policy checks funds, transaction value, and recent execution activity.
7. The customer reviews a frozen summary and approves it. Higher-value requests require the session PIN and, at the highest tier, simulated registered-device confirmation.
8. The execution gateway verifies the mock transaction proof, rejects expired or reused approval, checks the balance projection, and atomically updates mock balances.
9. The engine records the transaction outcome and control events. Later balance enquiries require PIN verification.

### Technical architecture

The browser uses HTML, CSS, and JavaScript. A Python standard-library HTTP server exposes the API. The transaction engine owns policy, recipient resolution, session PIN/KYC state, balance projection, authorization, execution, and audit events.

The intent adapter supports Tencent TokenHub structured output and a deterministic local fallback. Its role is to propose typed actions. The independent validator, policy checks, and execution code remain separate from that extraction step. Monetary amounts are represented as integer cents, and a fingerprint binds approval to the frozen batch details. Final execution uses a lock to prevent overlapping approvals from executing the same draft twice.

Dependencies follow this flow:

```text
Browser -> HTTP API -> Transaction engine
                       |-> Intent adapter -> TokenHub or local parser
                       |-> Independent transcript facts and validator
                       |-> Account/payee metadata and policy
                       |-> Frozen approval -> Mock execution -> Audit
```

### How prompts drive AI generation

When TokenHub is configured, the adapter provides a system instruction to extract only actions explicitly requested by the customer, avoid inferring missing recipients, amounts, accounts, assets, or quantities, and preserve an exact transcript segment. Customer text is passed as a separate user message.

A JSON schema constrains candidate fields such as action kind, amount, recipient, source account, asset, and share quantity. The engine treats the resulting candidates as untrusted input. It resolves identities and validates transcript consistency before offering an authorization draft. An unavailable or invalid model response triggers the local fallback, with the fallback reason recorded in the audit.

The Render deployment verified on 16 October 2026 uses the deterministic local provider because TokenHub credentials are not configured. Runtime model performance is therefore not claimed for this deployment.

### Security controls demonstrated

- Session KYC blocks drafting until the server records mock verification.
- PIN verifiers use salted PBKDF2; repeated incorrect attempts temporarily lock verification.
- Amount, beneficiary, action type/count, source account, asset, and quantity are checked against transcript facts where extracted.
- Explicit approval signs the exact draft using a server-generated mock HMAC proof.
- Authorizations expire after five minutes and are single-use.
- Combined transaction debits of SGD 10,000 or more require PIN step-up; SGD 50,000 or more additionally require simulated device confirmation. These totals include investment purchases and are prototype settings, not official DBS thresholds.
- A batch above SGD 100,000 is blocked, and recent executions are subject to a velocity rule.
- Stale balance projections block execution; final balance mutation is atomic within the process.
- Recognized prompt-injection patterns are blocked before drafting.

### Prototype boundaries

SurePay moves no real money, executes no real trades, and has no live DBS integration. KYC, account balances, stock prices, recipient verification, device confirmation, and biometric approval are simulations. The hold interaction obtains a server-generated HMAC proof; it is not native FaceID, WebAuthn, or a client hardware-backed signature.

The parser and semantic firewall cover a bounded set of phrases and attacks; arbitrary multilingual and adversarial understanding has not been demonstrated. Browser speech support varies by device. Audit and financial state are in memory; added mock recipients are stored locally and are not durable on Render Free. The deployment shares one mock account ledger across visitors. Production work would require authenticated customer ownership, durable per-customer storage, full authorization/session binding, bank identity and signing services, and broader security evaluation.

## Business value and evaluation

The intended impact is fewer navigation steps for combined financial tasks, better visibility of transaction details, and a clear separation between conversational interpretation and execution authority. One request can express a transfer and investment, and one summary exposes both actions for review.

On 16 October 2026, a fresh checkout of GitHub commit `c899f9ee4adfb8852879df3accf3dbbbda2c992c` passed **46 of 46 automated tests** using `python -B -m unittest discover -s tests -v` on build `20261004.1`. The run completed in approximately 2.2 seconds. This is test-suite runtime, not customer transaction latency. The browser JavaScript also passed `node --check web/app.js`.

The live Render deployment returned HTTP 200 and a healthy backend status. **Nine of nine API smoke checks passed**: KYC gating, successful mock KYC, wrong-PIN balance denial, correct-PIN balance disclosure, two-action drafting, duplicate-name clarification, recognized injection rejection, no PIN step-up at SGD 8,000, and PIN step-up at SGD 10,000. Transaction drafts were cancelled; no payments were executed during these live checks. These checks do not replace a full browser interaction test.

The suite covers KYC gating, ambiguous and unknown recipients, transcript mismatches, account selection, protected balance disclosure, PIN step-up, unsigned execution rejection, expired approval, replay rejection, and concurrent approval. In the tested concurrent duplicate-approval case, one request executed and the other was blocked.

These results establish behavior for the tested cases, not a universal attack-blocking rate. Intent-extraction accuracy, request-to-review latency, user completion rate, and reductions in menu navigation remain evaluation goals. Future assessment will compare the conversational flow with a conventional form flow using a curated prompt set and user tasks.

## Development and submission evidence

Development used AI assistance for implementation and review. CodeBuddy Studio conversation screenshots document a KYC development task and its file changes in the separate React/.NET workspace named `tencent`. The final SurePay artifact is the Python/JavaScript project; its session-bound mock KYC implementation and 46-test result were subsequently verified in this folder.

The selected Studio screenshots should be described as evidence of that prototype development task. They do not show the final Python implementation. Any final-project CodeBuddy conversation records can be added as supplementary evidence when available. Earlier development also used Codex; the build history should retain both tool contributions accurately.

## Demo access and judge walkthrough

Public demo: https://surepay-dcta-1.onrender.com/

This HTTPS deployment runs on Render independently of the developer's computer. Render Free sleeps after 15 minutes without traffic and may take about one minute to wake when opened. In-memory sessions and balances reset when the process restarts, and local file changes are not durable. Recheck availability before entering the submission form.

1. Create any six-digit demo PIN. Use that same PIN for protected actions.
2. Enter `SUREPAY-DEMO-2026` on the mock KYC screen.
3. Request “Send $80 to Maya from my current account and buy 2 Apple shares.”
4. Review both actions and hold the approval button.
5. Use Show Balance and verify with the demo PIN.
6. Request “Send $50 to John” to demonstrate clarification.
7. Request “Send $50 to Maya, actually make that $500” to demonstrate discrepancy blocking.
8. Request “Transfer $10000 to Alex” to demonstrate PIN step-up.

Use only fictional data throughout the demonstration.
