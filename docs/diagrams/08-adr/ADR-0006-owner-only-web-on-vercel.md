# ADR-0006 — Web owner-only บน Vercel เรียก API ฝั่ง server ด้วย automation token

- Status: accepted (retro-documented)

## Decision
- Next.js (`web/`) บน Vercel project `solo-accounts-web`; sign-in ด้วย password (scrypt) + TOTP หรือ OIDC (Google); subject ต้องอยู่ใน `ACCOUNTS_WEB_OWNER_SUBJECTS` (ต้องมีหนึ่ง entry)
- Session cookie `__Host-accounts-session` sealed (JWE dir/A256GCM) 8 ชั่วโมง, revoke ทั้งหมดด้วย `ACCOUNTS_WEB_SESSION_GENERATION`
- เรียก accounts-api server-side ด้วย `accounts-web` automation token (30 วัน, `accounts.*`) ที่ไม่ถึง browser; ต่ออายุด้วย `scripts/renew-web-token.sh`
- nonce CSP ทุก request (`web/proxy.ts`)

## Consequences
- Deploy web เป็น manual `vercel deploy --prod` (README) — ไม่ผูกกับ Railway CD
- lockout อยู่ใน memory ต่อ instance

Evidence: `web/lib/auth.ts`, `web/lib/auth-routes.ts`, `web/lib/password.ts`, `web/lib/api.ts`, `web/proxy.ts`, `scripts/renew-web-token.sh`, `README.md` §Web, `web/package.json`
