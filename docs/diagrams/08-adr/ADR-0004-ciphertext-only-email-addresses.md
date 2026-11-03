# ADR-0004 — API และ database เห็นเฉพาะ ciphertext ของ email address; ไม่เก็บ secret

- Status: accepted (retro-documented)

## Decision
- Web backend เข้ารหัส address ด้วย AES-256-GCM (key derive ต่อ tenant ด้วย HKDF จาก `ACCOUNTS_WEB_FIELD_KEY`, AAD ผูก tenant + hash) และส่ง HMAC-SHA256 keyed hash เพื่อ uniqueness; envelope `v1:<kid>:...`
- DB check constraint ปฏิเสธค่าที่มี `@` ใน `address_ciphertext`/`address_hash` (migration 0002)
- ไม่เก็บ password, recovery code, TOTP seed, cookie, token — ใช้ `vault_ref` ชี้ไป password manager; trust zone หยุดที่ `z2-separated` (Z3 ไม่รับ)
- Risk report ตั้งชื่อ mailbox ด้วย `address_hint` เท่านั้น

## Consequences
- เสีย `ACCOUNTS_WEB_FIELD_KEY` = อ่าน address ไม่ได้ (ต้องเก็บสำเนาใน vault)
- API client อื่น (MCP, automation) ต้องเข้ารหัสเองก่อนสร้าง mailbox

Evidence: `web/lib/crypto.ts`, `web/lib/form.ts`, `migrations/0002_ciphertext_only.sql`, `cell.yaml` header comment, `src/solo_accounts/routes.py`, `README.md` §What it never stores
