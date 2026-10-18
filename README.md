# platform-accounts-api
The Accounts cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `platform-accounts-api`, service `accounts-api` (Serverless) |
| Data | Neon project `platform-accounts-api`, database `accounts` |
| Web | `web/` (Next.js), Vercel project `solo-accounts-web`, owner-only sign-in |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`accounts`) |

An inventory of identities, mailboxes, platform accounts and domains with their trust zones,
recovery chains and MFA posture, built to become a multi-tenant SaaS (every row is scoped to a
workspace by forced row-level security).

## What it never stores

- **Secrets:** no passwords, recovery codes, TOTP seeds, cookies or tokens. `vault_ref` names the
  password-manager item instead.
- **Plaintext email addresses:** the web backend encrypts each address (AES-256-GCM, key derived per
  tenant from `ACCOUNTS_WEB_FIELD_KEY`) and sends a keyed hash for uniqueness. The API and the
  database only see `v1:` envelopes; a check constraint refuses any value containing `@`.
  Losing `ACCOUNTS_WEB_FIELD_KEY` makes the stored addresses unreadable: keep a copy in the vault.
- **Strictly isolated (Z3) personas:** `trust_zone` stops at `z2-separated`. A Z3 persona belongs only
  in its own vault, never next to the owner's real identity.

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `accounts.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/identities` | identity | `trust_zone`, `isolation_group`, `relation`, `status` |
| `/v1/domains` | domain | `identity_id`, `status`, `auto_renew` |
| `/v1/mailboxes` | mailbox | `identity_id`, `domain_id`, `kind`, `provider`, `status`, `recovery_mailbox_id`, `forwards_to_id`, `mfa_method` |
| `/v1/accounts` | account | `identity_id`, `platform`, `kind`, `status`, `login_mailbox_id`, `admin_account_id`, `mfa_primary` |

Custom route (`src/solo_accounts/routes.py`): `GET /v1/risk-report` needs read on all four resources and
returns findings (`recovery_hub_unprotected`, `recovery_cycle`, `recovery_not_live`, `recovery_via_work`,
`weak_mfa`, `zone_crossing_login`, `zone_crossing_admin`, `social_login_separated`,
`phone_bound_separated`, `login_mailbox_not_live`, `domain_release_takeover`, `domain_expiring`,
`review_overdue`) named by `address_hint`, never by address.

## Web

`web/` signs the owner in with a password plus an authenticator code (`node scripts/set-password.ts`
in `web/` stores the scrypt hash and TOTP secret in Vercel), or through OIDC (Google; another IdP such
as Clerk for a multi-tenant SaaS); failed password attempts lock a client out for 15 minutes, maps the subject to a tenant (`ACCOUNTS_WEB_OWNER_SUBJECTS`), and calls the API server-side
with the `accounts-web` automation token (empire-platform, 30 days, `accounts.*` only). The token,
field key and session key never reach the browser. Variables: see `web/.env.example`.

The `accounts-web` token lives with the other automation tokens in `~/.config/empire-platform/tokens`, so
`empire-monitor` warns 7 days before it expires; then run `scripts/renew-web-token.sh`. To sign every
browser out, bump `ACCOUNTS_WEB_SESSION_GENERATION` in Vercel and redeploy. Every page carries a
per-request nonce CSP (`web/proxy.ts`).

```bash
cd web && npm install && npm test && npm run typecheck && npm run build
vercel deploy --prod   # project solo-accounts-web; variables set in Vercel, never in the repository
```

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/accounts-db provision
npm install && railway config apply && railway up --ci --service accounts-api
railway scale --service accounts-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see
`src/cellkit/_sentry.py`), `ACCOUNTS_DB_MODE=hosted`, `ACCOUNTS_DB_URL_API`,
`ACCOUNTS_JWT_PUBLIC_KEY_PEM`, `ACCOUNTS_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
