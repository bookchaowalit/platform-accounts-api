# 01 — Business process (As-Is / To-Be)

ระบบนี้คือ **Accounts cell**: inventory ของ identity, mailbox, platform account และ domain ของ owner พร้อม trust zone, recovery chain และ MFA posture เพื่อให้เห็นความเสี่ยง (เสีย mailbox เดียวแล้วเสียหลายบัญชี, domain หมดอายุ, brand ที่แยกไว้ถูกโยงกลับมาหา owner) ก่อนเกิดเหตุจริง ผ่าน `GET /v1/risk-report` ระบบ **ไม่เก็บ secret** (password, recovery code, TOTP seed) และ **ไม่เห็น email แบบ plaintext** เลย

## As-Is (จาก code วันนี้)

```mermaid
flowchart TD
  A["Owner signs in to solo-accounts-web"] --> B["Enter or edit identity, domain, mailbox, account"]
  B --> C["Web backend encrypts email address (AES-256-GCM) and computes keyed hash"]
  C --> D["Server action calls accounts-api with accounts-web token"]
  D --> E{"empire-platform authz decide / execution begin"}
  E -->|"deny"| F["403 shown in Thai error message"]
  E -->|"allow"| G["Row written in Neon under workspace RLS"]
  G --> H["Execution finished with before/after row hashes (audit)"]
  H --> I["Owner opens overview page"]
  I --> J["GET /v1/risk-report analyses all four resources"]
  J --> K["Findings by severity: high / medium / low / info"]
  K --> L["Owner fixes record: add security key, change recovery mailbox, renew domain, review mailbox"]
  L --> B
  M["Agents via accounts-mcp or remote MCP hub"] --> D
  N["Solo Web /accounts module"] --> O["accounts-metadata-api reads ACCOUNT-MATRIX.yaml (read-only)"]
```

Sources: `README.md`, `PRODUCT.md`, `cell.yaml`, `src/solo_accounts/routes.py`, `src/cellkit/app.py`, `web/app/actions.ts`, `web/app/page.tsx`, `web/lib/crypto.ts`, `services/accounts-metadata-api/server.py`, `accounts/ACCOUNT-MATRIX.yaml`

### ขั้นตอนหลัก
1. **บันทึก inventory**: owner กรอกผ่าน web (หรือ import JSON ด้วย `web/scripts/import.ts` ที่เข้ารหัส address ระหว่างทาง, re-run ได้เพราะ match ด้วย natural key)
2. **ควบคุมสิทธิ์และ audit**: ทุก write ผ่าน empire-platform (`/v1/authz/decide`, `/v1/executions`, `/finish`)
3. **ประเมินความเสี่ยง**: risk report 13 finding codes (ดู `README.md`) เป้าหมายใน `PRODUCT.md` คือ "ไม่มี `high` finding ที่ไม่มีคำอธิบาย"
4. **ระบบเดิม (matrix)**: `accounts/` folder + `ACCOUNT-MATRIX.yaml` ยังถูก serve read-only ผ่าน `accounts-metadata-api`

## To-Be

จาก `PRODUCT.md` (ไม่มี `docs/UPGRADE-PLAN.md` หรือ spec ที่เป็น feature ใหม่; `specs/001-l2-baseline` เป็น tooling/test baseline):
- "built to become a multi-tenant SaaS" — OIDC ผ่าน IdP อื่น เช่น Clerk สำหรับ multi-tenant (`README.md` §Web)
- Measures ที่ต้องมี dashboard: high findings over time, `review_overdue`, weak MFA, 5xx/p95 (`PRODUCT.md` ระบุ "[ต้องยืนยัน: no dashboard records these yet]")

```mermaid
flowchart LR
  T1["Today: one owner tenant (ACCOUNTS_WEB_OWNER_SUBJECTS has exactly one entry)"] --> T2["To-Be: multi-tenant SaaS, workspace per tenant (RLS already per workspace)"]
  T2 --> T3["To-Be: measures tracked on a dashboard"]
```

Sources: `PRODUCT.md`, `README.md`, `web/lib/auth.ts`, `migrations/0001_accounts.sql`

## Open questions
- Solo Web (`life-dashboard-web`) ยังเรียก `accounts-metadata-api` อยู่หรือไม่ หลัง `accounts-api` มาแทน matrix (`PRODUCT.md` [ต้องยืนยัน])
- แผน multi-tenant: timeline และ IdP ที่เลือก ไม่มีใน repo
- Google OIDC client id/secret ของ web ยังไม่ตั้ง (`PRODUCT.md` [ต้องยืนยัน])
