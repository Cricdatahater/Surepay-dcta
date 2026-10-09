# DBS requirements traceability

Source: contest problem brief, pages 3–8. Selected case: **Scenario 1 —
Voice-Enabled Payment and Transaction**.

| Brief requirement | Prototype evidence | Automated evidence |
|---|---|---|
| Voice or text input | Browser speech recognition plus text composer | Manual browser demo |
| Multi-intent structured drafts | Transfers plus share-quantity or monetary-value investments compile into one batch | `test_multi_intent_compiles_atomic_batch`, `test_investment_accepts_monetary_amount` |
| Dynamic ambiguity resolution | Two saved Johns produce targeted payee choices | `test_ambiguous_recipient_requires_targeted_choice` |
| Independent validation agent | Read-only transcript facts are compared with compiled actions | `test_dual_engine_freezes_discrepant_amounts` |
| Deterministic HITL overlay | Exact actions shown outside chat; hold-to-authorize | Browser demo |
| Biometric cryptographic authorization | Mock FaceID produces batch-bound HMAC signature | `test_unsigned_execution_is_cryptographically_rejected` |
| Zero-trust API gateway | Execution rejects absent/invalid signatures | Same test plus gateway path |
| Prompt-injection shielding | Semantic firewall runs before drafting | `test_prompt_injection_is_blocked_before_drafting` |
| Risk and value thresholds | High-value requests require step-up; hard batch limit | `test_high_value_requires_step_up` |
| Velocity throttling | More than three recent executions pauses the channel | Engine policy; test planned |
| Traceable and auditable | Raw input, draft, validation, policy, signature, execution logged | `test_audit_records_full_control_sequence` |
| KYC/basic risk control | Session setup requires a mock customer-reference check; the engine rejects chat before intent extraction until server-side KYC status is verified | `test_incomplete_kyc_blocks_before_intent_extraction`, `test_mock_kyc_must_pass_server_verification_before_drafting` |
| Real bank services optional | All execution and biometrics clearly marked mock | README and UI disclosure |

## Honest prototype boundaries

- Web Speech API is a browser capability, not a production bank STT service.
- The HMAC biometric signer simulates a trusted device enclave. Production should
  use platform WebAuthn/passkeys or the bank's native biometric SDK.
- Execution is in memory and moves no funds.
- The validator is deliberately simple and deterministic today; a second model
  with separate prompts/model family should be evaluated without gaining write
  privileges.
- The KYC reference check is a deterministic simulation only. Production needs
  an authenticated customer-profile, identity-verification, and sanctions/status
  service; the demo reference is not an identity credential.
