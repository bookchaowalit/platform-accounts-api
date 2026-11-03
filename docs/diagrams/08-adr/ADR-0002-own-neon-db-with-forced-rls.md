# ADR-0002 — Database ของตัวเองบน Neon พร้อม forced row-level security ต่อ workspace

- Status: accepted (retro-documented)

## Context
ข้อมูลเป็น inventory ส่วนตัวที่อ่อนไหว และ product ตั้งใจเป็น multi-tenant SaaS ในอนาคต

## Decision
- Neon project `platform-accounts-api`, database `accounts`, region default `aws-ap-southeast-1` (`accounts-db provision`)
- ทุกตารางมี `workspace_id` และ `ENABLE` + `FORCE ROW LEVEL SECURITY` policy `workspace_isolation` จาก `accounts.current_workspace()` (`app.workspace_id` ต่อ transaction)
- แยก role: `accounts_migrator` (owner schema), `accounts_api` (NOBYPASSRLS, owns nothing), `accounts_publisher` (outbox only)
- Migration append-only

## Consequences
- workspace isolation บังคับที่ DB แม้ code มี bug
- free quota ของ Neon เป็นต่อ project (ops record: neon-platform-quota (2026-11-03) — ระบุหลักการทั่วไป ไม่ได้ระบุ repo นี้)

Evidence: `migrations/0001_accounts.sql`, `db/roles.sql`, `src/cellkit/db.py`, `src/cellkit/server.py`, `src/cellkit/app.py` `bound()`, `README.md`, `AGENTS.md`
