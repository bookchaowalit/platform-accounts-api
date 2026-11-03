# ADR-0003 — Authorization, execution record และ audit อยู่ที่ empire-platform

- Status: accepted (retro-documented)

## Decision
- Token RS256 ออกโดย empire-platform; cell ตรวจ local (PEM หรือ JWKS, audience `accounts-api`, issuer; hosted ปฏิเสธ issuer `empire-platform-dev`) เพื่อ bind workspace สำหรับ RLS
- ทุก read เรียก `POST /v1/authz/decide`; ทุก write: precheck → local transaction → `POST /v1/executions` (ผูกกับ record และ permission + idempotency key) → commit → `POST /v1/executions/{id}/finish` พร้อม before/after row hash
- token ของผู้เรียกถูกส่งต่อ (ไม่มี service account ของ cell เอง); platform ล่ม = 503 `authorization_unavailable`

## Consequences
- audit trail รวมศูนย์; cell ไม่มีตาราง audit เอง
- availability ของ cell ขึ้นกับ empire-platform
- ถ้า finish ล้มเหลว write ยังสำเร็จ แค่ log + Sentry `capture`

Evidence: `src/cellkit/auth.py`, `src/cellkit/platform.py`, `src/cellkit/app.py` (`allow`, `write`), `src/cellkit/server.py`, `README.md`
