# Core 22 SDLC diagram pack — platform-accounts-api

ชุด diagram 22 รายการตาม SDLC Diagram Catalog v2 (knowledge-base `knowledge/tech/core-cs/sdlc-diagram-catalog.md`) วาดจาก code / config ของ repo นี้ที่ `origin/main` `e7de6ce` (2026-10-24) อ่านเมื่อ 2026-11-04

repo นี้คือ **Accounts cell**: `accounts-api` (FastAPI จาก `cell.yaml`, Railway Serverless, Neon พร้อม forced RLS), `accounts-metadata-api` (read-only projection ของ `accounts/ACCOUNT-MATRIX.yaml`), `solo-accounts-web` (Next.js owner-only บน Vercel) และ `accounts-mcp` (stdio) Authorization / execution / audit อยู่ที่ empire-platform ทุก diagram มี `Sources:` และ "Open questions" แยกไว้ ข้อมูล runtime ที่ไม่อยู่ใน repo อ้าง Railway API (read-only, 2026-11-04), repo ข้างเคียงแบบ read-only (`platform-uptime-worker`, `platform-mcp-remote-worker`, `platform-db-backup`) และ ops record

| # | Item | Status | File | Sources read |
|---|---|---|---|---|
| 01 | Business process (As-Is / To-Be) | done | [01-business-process.md](01-business-process.md) | README.md, PRODUCT.md, cell.yaml, routes.py, app.py, web/app, web/lib/crypto.ts |
| 02 | Use cases | done | [02-use-cases.md](02-use-cases.md) | app.py, mcp.py, routes.py, web/lib/auth*.ts, metadata server.py, AGENTS.md |
| 03 | User flows | done | [03-user-flows.md](03-user-flows.md) | web/app/**, web/lib/auth-routes.ts, session.ts, records.ts, form.ts |
| 04 | Traceability (RTM) | done | [04-traceability.md](04-traceability.md) | PRODUCT.md, specs/001-l2-baseline/spec.md, tests/, web/tests/, ci.yml |
| 05 | C4 Context | done | [05-c4-context.md](05-c4-context.md) | README.md, PRODUCT.md, platform.py, .mcp.json, uptime targets.ts |
| 06 | C4 Container | done | [06-c4-container.md](06-c4-container.md) | .railway/railway.ts, Dockerfiles, web/package.json, pyproject.toml, db/roles.sql |
| 07 | C4 Component (accounts-api) | done | [07-c4-component.md](07-c4-component.md) | src/cellkit/*.py, src/solo_accounts/routes.py |
| 08 | ADRs (6) | done | [08-adr/](08-adr/) | cell.yaml, migrations, cellkit, web/lib, railway.ts, cellkit-notes.md |
| 09 | ERD | done | [09-erd.md](09-erd.md) | migrations/0001, 0002, cell.yaml |
| 10 | Sequences (4) | done | [10-sequences.md](10-sequences.md) | actions.ts, crypto.ts, app.py, platform.py, routes.py, auth-routes.ts, metadata server.py |
| 11 | State machines | done (enum values; API does not enforce transitions) | [11-state-machines.md](11-state-machines.md) | cell.yaml, migrations, routes.py |
| 12 | API and integrations | done | [12-api-integration.md](12-api-integration.md) | app.py, routes.py, metadata server.py, web/lib/api.ts, auth.ts, db.py |
| 13 | Threat model (DFD + STRIDE) | done | [13-threat-model.md](13-threat-model.md) | web/lib/*, proxy.ts, auth.py, app.py, _sentry.py, migrations, roles.sql, gh branch protection API |
| 14 | Backup / DR | done (central backup coverage unverified; RTO/RPO not defined) | [14-backup-dr.md](14-backup-dr.md) | README.md, db.py, crypto.ts, platform-db-backup, ops record |
| 15 | CI/CD pipeline | done | [15-cicd-pipeline.md](15-cicd-pipeline.md) | ci.yml, railway.ts, railway.toml, README.md |
| 16 | Deployment | done | [16-deployment.md](16-deployment.md) | railway.ts, Dockerfiles, README.md, PRODUCT.md, Railway API |
| 17 | Test coverage matrix | done | [17-test-coverage-matrix.md](17-test-coverage-matrix.md) | tests/, contract.py, web/tests/, metadata tests, ci.yml |
| 18 | Git / release workflow | done | [18-git-release-workflow.md](18-git-release-workflow.md) | git log, gh pr list, gh branch protection API, AGENTS.md |
| 19 | Service dependency map | done | [19-service-dependency-map.md](19-service-dependency-map.md) | app.py, auth.py, web/lib/api.ts, uptime targets.ts, mcp-remote worker.ts |
| 20 | Observability | done | [20-observability.md](20-observability.md) | _sentry.py (both), app.py, README.md, PRODUCT.md, uptime targets.ts, ops record |
| 21 | Incident response | done | [21-incident-response.md](21-incident-response.md) | README.md, AGENTS.md, renew-web-token.sh, ops records |
| 22 | DORA | done (recovery time not computable: no failed deploy) | [22-dora.md](22-dora.md) | Railway API, git log, gh run list, gh pr list |

## ADRs (retro-documented)

- [ADR-0001](08-adr/ADR-0001-cell-from-spec-with-own-cellkit.md) Cell จาก `cell.yaml`, repo เป็นเจ้าของ `cellkit`
- [ADR-0002](08-adr/ADR-0002-own-neon-db-with-forced-rls.md) Neon DB ของตัวเอง + forced RLS ต่อ workspace + role separation
- [ADR-0003](08-adr/ADR-0003-authz-and-audit-in-empire-platform.md) Authz / executions / audit ที่ empire-platform
- [ADR-0004](08-adr/ADR-0004-ciphertext-only-email-addresses.md) API/DB เห็นเฉพาะ ciphertext; ไม่เก็บ secret
- [ADR-0005](08-adr/ADR-0005-railway-serverless-cd-from-main.md) Railway Serverless Singapore, CD จาก `main` หลัง CI
- [ADR-0006](08-adr/ADR-0006-owner-only-web-on-vercel.md) Web owner-only บน Vercel ด้วย automation token ฝั่ง server

## Related docs (reused, not copied)

- [`README.md`](../../README.md), [`PRODUCT.md`](../../PRODUCT.md), [`AGENTS.md`](../../AGENTS.md)
- [`docs/cellkit-notes.md`](../cellkit-notes.md)
- [`specs/001-l2-baseline/spec.md`](../../specs/001-l2-baseline/spec.md)
- [`services/accounts-metadata-api/contracts/accounts.v1.md`](../../services/accounts-metadata-api/contracts/accounts.v1.md)
- Central: [ADR-0004 TDD + SDD](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md), [ADR-0002 production baseline](https://github.com/bookchaowalit/architecture-docs/blob/main/docs/architecture/decisions/ADR-0002-production-baseline-monitoring-backups.md)

## Open questions for the owner (summary)

1. `accounts` DB อยู่ใน `BACKUP_TARGETS` ของ `ops-backups/db-backup` หรือไม่; Neon retention; RTO/RPO
2. สำเนา `ACCOUNTS_WEB_FIELD_KEY` อยู่ใน vault; ขั้นตอน rotate key (`k2`)
3. `SENTRY_DSN` ตั้งแล้วบนทั้งสอง Railway service หรือไม่
4. Solo Web ยังเรียก `accounts-metadata-api` อยู่หรือไม่; `service.yaml` ยังเขียน `deploy.target: unassigned`
5. Google OIDC client ของ web ยังไม่ตั้ง
6. Branch protection บน `main` (ตอนนี้ไม่มี)
7. สาเหตุ redeploy 2026-10-30 (ไม่มี creator)
8. SPEC-001 "changes requested" — ใครปิด
