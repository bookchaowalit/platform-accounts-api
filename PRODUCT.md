# Product

<!-- impeccable:product-schema 1 -->

## Platform

api (two Railway services) plus a small owner-only web app (`web/`, Next.js on Vercel)

## Users

- The Solo Empire owner, through `web/` (Vercel project `solo-accounts-web`, password + authenticator
  code or OIDC sign-in), which calls the API server-side with the `accounts-web` automation token.
- The owner's agents, through the cell's MCP server (`accounts-mcp`) and the hosted tool hub
  (`platform-mcp-remote-worker`, which lists `accounts-api-production-cfee.up.railway.app`).
- Automations with an `empire-platform` token, within the permissions
  `accounts.identity|domain|mailbox|account:read|write|delete`.
- `accounts-metadata-api`: the `/accounts` module of Solo Web (`life-dashboard-web`), reading a JSON
  projection of `accounts/ACCOUNT-MATRIX.yaml` with an owner-scoped RS256 service JWT. Whether Solo Web
  still calls it now that `accounts-api` supersedes the matrix (registry note) is [ต้องยืนยัน].

## Product Purpose

One inventory of the owner's identities, mailboxes, platform accounts and domains with their trust
zones, recovery chains and MFA posture, so that losing one mailbox, letting one domain lapse or
linking a separated brand to the owner is visible before it happens (`GET /v1/risk-report`).

Success: every real account and mailbox is recorded once, the risk report has no `high` finding left
unexplained, and nothing in the inventory could be used to sign in (no secrets, no plaintext addresses).

## Positioning

One capability, one service: its own API (Railway, Serverless), its own database (Neon) with forced
row-level security per workspace, and authorization, executions and audit through `empire-platform`.
It is deliberately not a password manager: `vault_ref` points at the password-manager item, and
strictly isolated (Z3) personas are refused so they never sit next to the owner's real identity.

## Operating Context

- Production `accounts-api`: `https://accounts-api-production-cfee.up.railway.app` (`/health`).
- Production `accounts-metadata-api`: `https://accounts-metadata-api-production.up.railway.app`
  (`/health` liveness, `/ready` for the Railway health check), the URL `platform-uptime-worker`
  checks; it is not listed in `online-systems.yaml` [ต้องยืนยัน].
- Web: `https://solo-accounts-web.vercel.app`. Its Google OIDC client id and secret are still to be
  set (registry note) [ต้องยืนยัน].
- Both Railway services deploy from `main` after CI passes (Railway Wait for CI), sleep when idle and
  run in Singapore next to Neon. Monitored by `platform-uptime-worker`; errors go to Sentry only when
  `SENTRY_DSN` is set, without personal data.
- Email addresses arrive already encrypted by the web backend (`v1:` AES-256-GCM envelope plus an
  HMAC-SHA256 keyed hash per workspace); losing `ACCOUNTS_WEB_FIELD_KEY` makes them unreadable.

## Capabilities and Constraints

- `/v1/identities`, `/v1/domains`, `/v1/mailboxes`, `/v1/accounts`: list (with filters), stats, get,
  get-by-legacy-id, create (with `Idempotency-Key`), patch (with `expected_version`), delete.
- `GET /v1/risk-report`: needs read on all four resources; returns counts per severity and findings
  (`recovery_hub_unprotected`, `recovery_cycle`, `recovery_not_live`, `recovery_via_work`, `weak_mfa`,
  `zone_crossing_login`, `zone_crossing_admin`, `social_login_separated`, `phone_bound_separated`,
  `login_mailbox_not_live`, `domain_release_takeover`, `domain_expiring`, `review_overdue`) named by
  `address_hint`, never by address. At most 20,000 rows per resource (413 above) and 1,000 findings
  listed (`truncated`).
- Rules: `trust_zone` is one of `z0-root`, `z1-public`, `z2-business`, `z2-separated` (Z3 refused);
  identity `slug` and domain `name` are unique per workspace; a mailbox's `address_hash` is unique per
  workspace and neither it nor `address_ciphertext` may contain `@` (422 `invalid_value`);
  `security_keys` is 0 to 20; an account's `(platform, handle)` is unique; references must exist
  (422 `reference_not_found`); new accounts start `planned` with MFA `unknown`.
- `accounts-metadata-api`: `GET /health`, `GET /ready`, `GET /api/v1/accounts?status=&platform=&kind=&q=`
  over `accounts/ACCOUNT-MATRIX.yaml`, read-only, anonymous identities as counts only.
- Out of scope: passwords, recovery codes, TOTP seeds, sessions, and graph events (inventory stays in
  this cell).

## Measures

- `high` findings in the risk report over time (target: 0 unexplained).
- Live mailboxes with `review_overdue` (not reviewed in 180 days).
- Live accounts and mailboxes whose second factor is `sms`, `none` or `unknown`.
- 5xx rate and p95 latency on `/v1/*` and `/api/v1/accounts` (Sentry and uptime worker)
  [ต้องยืนยัน: no dashboard records these yet].
