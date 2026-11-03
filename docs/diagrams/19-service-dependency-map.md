# 19 — Service dependency map

```mermaid
flowchart LR
  subgraph consumers["Callers"]
    OWNER["Owner browser"]
    AG["accounts-mcp (owner machine)"]
    HUB["platform-mcp-remote-worker"]
    SW["Solo Web life-dashboard-web"]
    UP["platform-uptime-worker"]
  end
  WEB["solo-accounts-web (Vercel)"]
  API["accounts-api (Railway)"]
  META["accounts-metadata-api (Railway)"]
  EP["empire-platform: authz, executions, JWKS"]
  NEON[("Neon accounts DB")]
  SEN["Sentry"]
  IDP["Google OIDC"]
  MATRIX["ACCOUNT-MATRIX.yaml baked into image"]
  OWNER --> WEB
  WEB -->|"hard dependency"| API
  WEB -->|"optional sign-in"| IDP
  AG --> API
  HUB --> API
  SW --> META
  UP -->|"/health"| API
  UP -->|"/health"| META
  API -->|"hard: every request"| EP
  API -->|"hard"| NEON
  API -.->|"optional"| SEN
  META --> MATRIX
  META -.->|"optional"| SEN
```

| Dependency | Failure effect | Evidence |
|---|---|---|
| empire-platform down | reads and writes 503 `authorization_unavailable`; JWKS cache keeps last good keys | `src/cellkit/app.py`, `src/cellkit/auth.py` |
| Neon down | 503 `unavailable` | `src/cellkit/app.py` `bound()` |
| accounts-api asleep | first web request waits (timeout 20 s) | `web/lib/api.ts`, `.railway/railway.ts` |
| Sentry unset | error reporting off | `src/cellkit/_sentry.py` |

Sources: `src/cellkit/app.py`, `src/cellkit/auth.py`, `src/cellkit/platform.py`, `src/cellkit/_sentry.py`, `web/lib/api.ts`, `web/lib/auth.ts`, `services/accounts-metadata-api/Dockerfile`, `.railway/railway.ts`, `PRODUCT.md`, `platform-uptime-worker` `src/targets.ts` (read-only), `platform-mcp-remote-worker` `src/worker.ts` line 129 (read-only)

## Open questions
- empire-platform base URL (`EMPIRE_PLATFORM_URL`) ชี้ไป service ไหนหลังการแยก platform-identity (11-03) — ไม่อยู่ใน repo
