# ADR-0005 — Railway Serverless ใน Singapore, deploy จาก GitHub `main` หลัง CI ผ่าน

- Status: accepted (retro-documented), CD since 2026-10-18

## Decision
- Railway project `platform-accounts-api` สอง service: `accounts-api` (healthcheck `/health`) และ `accounts-metadata-api` (healthcheck `/ready`), `sleepApplication: true`
- source = GitHub `bookchaowalit/platform-accounts-api` branch `main`, `checkSuites: true` (Wait for CI); ไม่ใช้ `railway up`
- region `asia-southeast1-eqsg3a` ใกล้ Neon และ platform (ตั้งด้วย `railway scale` เพราะ IaC ไม่เก็บ region)
- Rollback = redeploy deployment ก่อนหน้าใน Railway

## Consequences
- CI แดง = production อยู่ที่ deployment เดิม
- cold start ตอนตื่น; web ตั้ง timeout 20 s (`web/lib/api.ts`)

Evidence: `.railway/railway.ts`, `services/accounts-metadata-api/railway.toml`, `README.md` §Develop and operate, `AGENTS.md`, `web/lib/api.ts`, Railway deployment list (project `platform-accounts-api`, read 2026-11-04: all deployments region `asia-southeast1-eqsg3a` except the first on 2026-10-10 in `us-east4-eqdc4a`)
