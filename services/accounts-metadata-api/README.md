# accounts-metadata-api (in accounts)

Moved out of solo-empire `services/accounts-api` on 2026-10-11 with its history (subtree add). A
read-only projection of the account matrix `accounts/ACCOUNT-MATRIX.yaml` for the Solo Web `/accounts`
module. **The matrix is read from this repository's root `accounts/` folder** (the file moves here from
solo-empire `accounts/`); override with `ACCOUNTS_API_MATRIX_PATH`. This service is separate from the
accounts cell API in `src/` (Postgres). `vendor/service-auth` is a vendored copy of
`bookchaowalit/platform-auth-sdk`.

Test (from this folder, as CI does): `uv sync --frozen --all-extras && .venv/bin/python -m coverage run -m unittest discover -s tests`
(the test against the real matrix is skipped until `accounts/ACCOUNT-MATRIX.yaml` exists here).
Dependencies are locked in this folder's `uv.lock` (the vendored `service-auth` is a path source in
it); the image installs them with `uv sync --frozen`. Change a dependency with `uv add`/`uv lock`
here and commit the lock.

---

# Solo Empire Accounts API

`accounts-api` is a small read-only backend that turns
[`accounts/ACCOUNT-MATRIX.yaml`](../../accounts/ACCOUNT-MATRIX.yaml) into JSON
for the `/accounts` module of [`solo-web`](../../projects/product/engineering/book-dev/github/bookchaowalit/private/life-dashboard-web/). The YAML
file stays the source that humans and AI agents edit; the service only reads
it and reloads when the file changes.

## Run

From the accounts repository root:

```bash
uv sync --frozen --project services/accounts-metadata-api   # the vendored service-auth comes with it
services/accounts-metadata-api/.venv/bin/python services/accounts-metadata-api/server.py
```

The default listener is `http://127.0.0.1:3470`. Configure
`ACCOUNTS_API_HOST`, `ACCOUNTS_API_PORT`, `ACCOUNTS_API_MATRIX_PATH`, and
`ACCOUNTS_API_CORS_ORIGINS` as needed. A non-loopback host requires valid scoped JWT configuration and enforces production authorization.

```text
GET /health
GET /api/v1/accounts?status=&platform=&kind=&q=
```

Anonymous identities are returned as counts only. See the
[Accounts API v1 contract](contracts/accounts.v1.md) for every field.

## Deploy

This folder is an independent deploy unit described by [`service.yaml`](service.yaml).
The accounts repository root is the Docker build context (service + vendored `service-auth` + `accounts/ACCOUNT-MATRIX.yaml`).

```bash
docker build -f services/accounts-metadata-api/Dockerfile -t solo-accounts-metadata-api .
```

The image enforces scoped JWT authorization and binds `0.0.0.0`.
`deploy.target` stays `unassigned` until the parent deployment configuration selects a target. See the decentralized services spec in solo-empire (`docs/superpowers/specs/2026-10-04-decentralized-services-and-storage-design.md`).

## Test

```bash
cd services/accounts-metadata-api && uv sync --frozen --all-extras
.venv/bin/python -m coverage run -m unittest discover -s tests -v && .venv/bin/python -m coverage report
.venv/bin/mypy . && uvx ruff@0.17.1 check . && uvx ruff@0.17.1 format --check .   # ruff.toml at the repository root
```

## Scoped authorization and readiness

[Railway configuration](railway.toml) selects the Dockerfile and `/ready`
health check (30 seconds), with at most 3 restarts after failure. It declares
no region, resources, runtime secret values, or existing cloud deployment.

Railway variable `SENTRY_DSN` turns on error reporting (unset = off, see [_sentry.py](_sentry.py)).

Configure `ACCOUNTS_API_AUTH_ISSUER` with the exact HTTPS origin of Solo Web,
`ACCOUNTS_API_AUTH_PUBLIC_KEY` with its PEM RSA public key (at least 2048 bits),
and `ACCOUNTS_API_AUTH_SUBJECTS` with the comma-separated allowed OIDC owner
subjects. See [.env.example](.env.example); provide configuration at runtime.
The signing private key belongs only to Solo Web and is never copied to this image.

Reads require an RS256 JWT: `iss` matches that origin, `aud=accounts-api`,
`sub` is allowed, `tenant_id=owner`, `scope=accounts:read`, and
`iat`, `nbf`, `exp`, `jti` are required. Lifetime is at most 120 seconds
with 5 seconds clock leeway. The verifier uses only the configured local key
and rejects remote key headers. Key rotation replaces the configured public
key and restarts the service; old signatures then fail. Missing configuration
returns `503 reads_disabled`; invalid tokens return `401 unauthorized`;
a valid token for another owner/tenant/scope returns `403 forbidden`.
Production never accepts `ACCOUNTS_API_TOKEN`. Partial JWT configuration
fails closed even in development.

`GET /health` is public liveness. `GET /ready` returns 200 only when the
source snapshot parses and JWT configuration is valid; otherwise it returns
503 with safe source/auth states. A local fixture with auth disabled reports
`auth=development`, not deployment readiness. Metadata contains a SHA-256
`revision` of its source snapshot and preserves its original dates.
Atomic source replacement triggers reload. This does not assert provider
freshness or a live deployment.

The listener accepts PaaS `PORT`; explicit `ACCOUNTS_API_PORT` or `--port`
takes precedence. Package installation is required; no sibling source-path
injection is used at runtime.
