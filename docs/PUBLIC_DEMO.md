# SurePay public demo

Verified on 5 October 2026 (Asia/Singapore).

## Current access

- Public HTTPS URL: https://excerpt-graphical-minor-instructors.trycloudflare.com
- Local origin: http://127.0.0.1:8000
- Build: `20261004.1`
- Runtime intent provider: `deterministic_local`; TokenHub is not configured.
- Server process ID at launch: `28632`.
- Tunnel process ID at launch: `14908`.

The public endpoint returned HTTP 200 and the correct health/build response.
The public API check returned `kyc_required` before verification and
`awaiting_authorization` afterward, with two validated actions in the mixed
transfer/investment draft. That check created a draft and moved no mock funds.

## Availability

This is a Cloudflare Quick Tunnel. The laptop must stay powered on, awake, and
connected to the internet. Both background processes must remain running.
Closing the browser alone does not stop them. Restarting the tunnel produces
a different URL; update the description and submission form if this happens.

Cloudflare provides no uptime guarantee for Quick Tunnels. Use this link for
sharing and rehearsals. Before final submission, arrange a hosted server or a
named tunnel with a stable domain that remains available throughout judging.
Creation of a public link does not itself guarantee contest bonus points.

## Visitor instructions

Create any six-digit demo PIN, then enter `SUREPAY-DEMO-2026` at mock KYC.
Only enter fictional recipient details and demo credentials.

The account ledger and recipient directory are shared mock data across
visitors. Transactions, PIN sessions, KYC, and audit state reset when the Python
server restarts; added recipients persist. A burst of demos may trigger the
global transaction velocity rule. This is a prototype, not an isolated
banking account for each visitor.

## Runtime files

The tunnel executable and logs are outside the submission source:

```text
C:\Users\comviva\.codex\visualizations\2026\09\20\01a0be1c-a308-7260-b7d8-fa16d2e52e23\cloudflared.exe
C:\Users\comviva\.codex\visualizations\2026\09\20\01a0be1c-a308-7260-b7d8-fa16d2e52e23\surepay-server.stdout.log
C:\Users\comviva\.codex\visualizations\2026\09\20\01a0be1c-a308-7260-b7d8-fa16d2e52e23\surepay-server.stderr.log
C:\Users\comviva\.codex\visualizations\2026\09\20\01a0be1c-a308-7260-b7d8-fa16d2e52e23\surepay-tunnel.stderr.log
```

To start again, run the application in one PowerShell terminal:

```powershell
Set-Location 'C:\Samridh\dcta-safe-transfer'
python app.py
```

In a second terminal, run:

```powershell
& 'C:\Users\comviva\.codex\visualizations\2026\09\20\01a0be1c-a308-7260-b7d8-fa16d2e52e23\cloudflared.exe' tunnel --no-autoupdate --protocol http2 --url http://127.0.0.1:8000
```

Use the newly printed HTTPS URL. If port 8000 is already serving the expected
build, use that existing origin rather than starting a second server.

To stop the currently launched background preview, first inspect its processes:

```powershell
Get-Process -Id 14908,28632
```

Verify that they are the `cloudflared` and `python` processes for this demo before
stopping them. Process IDs may be reused after an application exits.

## Official reference

[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)

## Submission description

Copy the four required project-description sections from
`docs/SUBMISSION_DESCRIPTION.md`. The title and six-word blurb are included.
The test result was reverified: 46/46 passed on 5 October 2026.
