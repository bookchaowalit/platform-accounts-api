# 06 — C4 Container

```mermaid
C4Container
  title Accounts cell - containers
  Person(owner, "Owner")
  System_Ext(agents, "Agents / MCP hub")
  System_Ext(soloweb, "Solo Web")
  System_Ext(platform, "empire-platform")
  System_Boundary(cell, "platform-accounts-api repository") {
    Container(web, "solo-accounts-web", "Next.js 16 on Vercel", "Owner sign-in, CRUD forms, overview; encrypts addresses server-side")
    Container(api, "accounts-api", "Python FastAPI (cellkit) on Railway Serverless", "/v1/identities, domains, mailboxes, accounts, risk-report")
    Container(mcp, "accounts-mcp", "Python stdio MCP server", "Tools accounts.<resource>.list|get|create|update|delete")
    Container(meta, "accounts-metadata-api", "Python stdlib HTTP on Railway Serverless", "Read-only projection of ACCOUNT-MATRIX.yaml")
    ContainerDb(db, "accounts database", "Neon PostgreSQL", "Schema accounts, forced RLS per workspace")
    Container(cli, "accounts-db / accounts-publish", "Python CLIs", "Provision Neon, migrate, sweep outbox")
  }
  Rel(owner, web, "HTTPS")
  Rel(web, api, "Bearer accounts-web token", "HTTPS")
  Rel(agents, mcp, "stdio")
  Rel(mcp, api, "Bearer caller token", "HTTPS")
  Rel(agents, api, "Remote hub calls", "HTTPS")
  Rel(soloweb, meta, "Service JWT", "HTTPS")
  Rel(api, db, "role accounts_api", "TLS")
  Rel(cli, db, "roles accounts_migrator / accounts_publisher", "TLS")
  Rel(api, platform, "decide / executions", "HTTPS")
```

| Container | Runtime | Evidence |
|---|---|---|
| accounts-api | `Dockerfile` (python:3.13-slim, `CMD accounts-api`), port 3623 (`cell.yaml`) | `.railway/railway.ts`, `src/cellkit/server.py` |
| accounts-metadata-api | `services/accounts-metadata-api/Dockerfile` (python:3.12-slim, port 3470) | `services/accounts-metadata-api/service.yaml`, `railway.toml` |
| solo-accounts-web | `web/package.json` (next 16.4.2), `web/vercel.json` | `README.md` §Web |
| accounts-mcp | `pyproject.toml` `[project.scripts]` | `.mcp.json`, `src/cellkit/mcp.py` |
| DB roles | `db/roles.sql` | `migrations/0001_accounts.sql` grants |

Sources: `.railway/railway.ts`, `Dockerfile`, `services/accounts-metadata-api/Dockerfile`, `services/accounts-metadata-api/service.yaml`, `web/package.json`, `web/vercel.json`, `pyproject.toml`, `.mcp.json`, `db/roles.sql`, `cell.yaml`

## Open questions
- `accounts-publish` ไม่มี Railway service/cron ใน `.railway/railway.ts` — ไม่ได้รัน (ไม่มี graph event อยู่แล้ว)
