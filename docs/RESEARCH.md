# Research dossier

Last verified: 20 September 2026 (Asia/Singapore).

## Confirmed event facts

- Event: AI CAN DO IT Tencent Cloud Hackathon Singapore 2026, co-hosted by
  Tencent Cloud and AI Singapore.
- Banking partner and track: DBS — Direct Conversational Transaction Agent.
- Confirmed brief: design a secure conversational transaction agent that
  interprets natural-language requests while transaction execution remains
  deterministic and subject to explicit user authorization.
- Timeline: kickoff 16 September; submission 16 October; finalists 23 October;
  Demo Day and awards 3 November 2026.
- Prize pool: SGD 17,000 (10,000 / 5,000 / 2,000).
- Each registered participant receives 1,000 CodeBuddy credits; official copy
  also names WorkBuddy and Miora among the available Tencent tools.
- Evaluation dimensions published in the launch release: relevance,
  human-centric design, use of AI, technical execution, feasibility,
  responsible AI, and potential business impact.
- Selected projects may be considered for proof-of-concept work, investment, or
  incubation; outstanding participants may receive Tencent internship fast-track
  consideration.

## DBS brief findings (pages 3–8)

- The team must identify its selected case at the beginning of the presentation.
  We select **Scenario 1: Voice-Enabled Payment and Transaction**.
- DCTA must support text or speech, multi-intent inputs, metadata retrieval, and
  structured transaction drafts.
- The mandatory architectural principle is zero trust: GenAI may generate drafts
  but must have no direct write permission to ledger APIs.
- The brief calls for dynamic ambiguity resolution, an independent read-only
  validation agent, a deterministic native confirmation overlay, biometric or
  hardware-token signing, gateway signature verification, injection shielding,
  risk/velocity throttling, and a complete audit trail.
- Real bank-grade biometrics and DBS execution gateway integration are explicitly
  not required; mock services are permitted.

## Product and regulatory context

- Singapore banks use transaction signing, fraud monitoring, and transaction
  alerts as digital-banking safeguards.
- Major banks introduced enhanced surveillance in October 2025: for protected
  accounts with balances of at least SGD 50,000, a transfer that brings rolling
  24-hour withdrawals over 50% of balance can be held for 24 hours or rejected.
- PayNow supports identifiers and QR-based transfers. These are strong future
  demo intents, but any prototype must resolve the identifier before approval.
- Tencent WorkBuddy itself follows a plan → confirm → execute → verifiable-result
  pattern. That interaction principle aligns well with the DCTA constraint.

## Sources

- Official event page: https://tch.tencentcloud.com/contest/44
- Tencent/AI Singapore launch release:
  https://en.prnasia.com/releases/apac/tencent-cloud-and-ai-singapore-connect-singapore-s-ai-talent-with-real-world-industry-challenges-548305.shtml
- Official launch listing: https://luma.com/26fqf3hy
- ABS fraud safeguards: https://www.abs.org.sg/industry-guidelines/compliance-and-risk-management/fraud
- ABS enhanced transaction surveillance release:
  https://www.abs.org.sg/docs/library/banks-to-launch-enhanced-safeguards-from-15-oct-2025-to-better-protect-accounts_.pdf
- ABS PayNow: https://www.abs.org.sg/e-payments/pay-now
- Tencent WorkBuddy guide: https://www-sg.tencentcloud.com/techpedia/144100?lang=en
- Tencent TokenHub docs: https://www-sg.tencentcloud.com/document/product/1300

## Still not specified / must ask organizers

As of verification, the official Developer Guides page says “No guides yet”. Do
not invent the following:

- Track-specific judging weights.
- Required deliverables, video length, repository/deployment fields.
- Team-size and eligibility limits.
- Whether a DBS sandbox, mock API, or sample data will be provided.
- Mandatory Tencent product usage versus encouraged usage.
- Cloud-credit activation and mentor/consultation schedule.

## Organizer questions (send immediately)

1. Could you share the full DBS DCTA challenge deck and evaluation weights?
2. Which transaction types are in scope: PayNow, FAST, bill pay, cards, or all?
3. Is a DBS/mock banking API or dataset available, and may teams simulate it?
4. What exactly constitutes explicit authorization in the challenge?
5. Which Tencent Cloud components are mandatory in the deployed solution?
6. What are the required submission artifacts and maximum demo-video length?
7. Are there constraints on external models, open-source packages, or hosting?
8. Will source code need to be public, and how is IP handled?
