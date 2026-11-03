# 05 — C4 Context

```mermaid
C4Context
  title Accounts cell - system context
  Person(owner, "Owner", "Solo Empire owner, signs in to the web app")
  System_Ext(agents, "Owner agents", "accounts-mcp (stdio) and platform-mcp-remote-worker")
  System_Ext(soloweb, "Solo Web", "life-dashboard-web /accounts module")
  System(accounts, "Accounts cell", "Inventory of identities, domains, mailboxes, accounts and risk report")
  System_Ext(platform, "empire-platform", "Identity tokens, authz decide, executions, audit")
  System_Ext(idp, "OIDC IdP", "Google (optional sign-in)")
  System_Ext(neon, "Neon", "Managed PostgreSQL")
  System_Ext(sentry, "Sentry", "Error reporting when SENTRY_DSN is set")
  System_Ext(uptime, "platform-uptime-worker", "Health checks of both Railway services")

  Rel(owner, accounts, "Uses", "HTTPS")
  Rel(agents, accounts, "Calls /v1/*", "HTTPS + caller token")
  Rel(soloweb, accounts, "Reads /api/v1/accounts", "HTTPS + service JWT")
  Rel(accounts, platform, "decide / begin / finish", "HTTPS")
  Rel(accounts, idp, "OIDC code flow", "HTTPS")
  Rel(accounts, neon, "SQL", "TLS")
  Rel(accounts, sentry, "Errors without PII")
  Rel(uptime, accounts, "GET /health")
```

| Element | Evidence |
|---|---|
| Owner, web | `README.md` §Web, `web/lib/auth.ts` |
| Agents | `.mcp.json`, `AGENTS.md`, `PRODUCT.md` Users (remote hub lists `accounts-api-production-cfee.up.railway.app`) |
| Solo Web | `PRODUCT.md` Users, `services/accounts-metadata-api/server.py` |
| empire-platform | `src/cellkit/platform.py` (`/v1/authz/decide`, `/v1/executions`) |
| Neon | `README.md`, `src/cellkit/db.py` (`NEON_API`) |
| Sentry | `src/cellkit/_sentry.py`, `services/accounts-metadata-api/_sentry.py` |
| Uptime | `PRODUCT.md` Operating Context; `platform-uptime-worker` `src/targets.ts` lines 44–45 (read-only check of sibling repo) |

Sources: `README.md`, `PRODUCT.md`, `AGENTS.md`, `.mcp.json`, `src/cellkit/platform.py`, `src/cellkit/db.py`, `src/cellkit/_sentry.py`, `web/lib/auth.ts`, `services/accounts-metadata-api/server.py`

## Open questions
- Solo Web ยังเป็น consumer จริงหรือไม่ (`PRODUCT.md` [ต้องยืนยัน])
- Cell นี้ยังไม่อยู่หลัง edge gateway `gateway.bookchaowalit.com` ตามที่ repo เห็น (ไม่มี config ใน repo) — ต้องยืนยันกับ registry
