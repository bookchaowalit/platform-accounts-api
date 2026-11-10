# 15 — CI/CD pipeline

Workflow เดียว `.github/workflows/ci.yml` (`CI`) triggers: push `main`, `pull_request`, `workflow_dispatch`; `concurrency: ci-<ref>` cancel-in-progress; `permissions: contents: read` ทุก job เป็น reusable workflow จาก `bookchaowalit/platform-ci-workflows` pinned SHA `87dc5e1` (v1.1.1) — repo public จึงใช้ GitHub-hosted runners (comment บรรทัดแรก)

```mermaid
flowchart TD
  T1["push main"] --> CI
  T2["pull_request"] --> CI
  T3["workflow_dispatch"] --> CI
  subgraph CI["CI workflow (4 parallel jobs, no needs)"]
    J1["accounts-api: ci-python.yml, Python 3.12, coverage gate 58"]
    J2["accounts-metadata-api: ci-python.yml, dir services/accounts-metadata-api, unittest + vendored service-auth, gate 78"]
    J3["web: ci-node.yml, Node 22, typecheck + vitest + next build"]
    J4["security: security.yml"]
  end
  CI -->|"all check suites green on main"| RW{"Railway Wait for CI (checkSuites: true)"}
  RW --> D1["Deploy accounts-api (Dockerfile, healthcheck /health)"]
  RW --> D2["Deploy accounts-metadata-api (services/.../Dockerfile, healthcheck /ready)"]
  CI -->|"any red"| STAY["Production stays on previous deployment"]
  MAN["Manual: vercel deploy --prod in web/"] --> V["Vercel solo-accounts-web"]
```

Sources: `.github/workflows/ci.yml`, `.railway/railway.ts`, `README.md` (Deploys, Web), `AGENTS.md`

## Open questions
- รายละเอียด step ภายใน reusable workflow (ruff, mypy, scanners) อยู่ใน `platform-ci-workflows@87dc5e1` ไม่ได้อ่านใน pack นี้
- Vercel project `solo-accounts-web` ผูก Git (push = deploy) หรือ manual เท่านั้น — README บอก manual
- lint ของ web ถูก skip ("No Biome/ESLint config yet")
