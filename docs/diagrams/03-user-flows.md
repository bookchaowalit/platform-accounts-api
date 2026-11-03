# 03 — User flows

Pages ใน `web/app/`: `/login`, `/` (overview + risk report), `/[resource]` (list + create form), `/[resource]/[id]` (edit/delete) และ route handlers `/auth/login`, `/auth/callback`, `/auth/password`, `/auth/logout` ข้อความ UI เป็นภาษาไทย

## Owner: sign in (password + TOTP หรือ OIDC)

```mermaid
flowchart TD
  S["Open any page"] --> R{"requireSession: valid __Host-accounts-session?"}
  R -->|"no"| L["/login"]
  L --> P["POST /auth/password (password + authenticator code)"]
  L --> O["GET /auth/login (OIDC, only when configured)"]
  P --> LK{"5 failures within 15 min for this client?"}
  LK -->|"yes"| E1["/login?error=locked"]
  LK -->|"no"| CK{"scrypt hash + TOTP valid?"}
  CK -->|"no"| E2["wait 600 ms, /login?error=password"]
  CK -->|"yes"| SES["Seal session (8 h, generation), redirect /"]
  O --> IDP["IdP authorize with PKCE + nonce"] --> CB["/auth/callback"]
  CB --> SUB{"Subject in ACCOUNTS_WEB_OWNER_SUBJECTS?"}
  SUB -->|"no"| E3["/login?error=denied"]
  SUB -->|"yes"| SES
  R -->|"yes"| PAGE["Render page"]
```

## Owner: บันทึกและแก้ไข record

```mermaid
flowchart TD
  A["/identities, /domains, /mailboxes or /accounts"] --> B["loadAll: list all four resources (limit 1000 pages), decrypt addresses"]
  B --> C["Fill RecordForm"]
  C --> D["createRecord server action"]
  D --> E["formToBody: address to ciphertext + hash + hint"]
  E --> F["POST /v1/<plural> with Idempotency-Key"]
  F -->|"201"| G["revalidate list and overview"]
  F -->|"409 / 422 / 403 / 503"| H["Thai error message (explain)"]
  A --> I["/<resource>/<id>"] --> J["updateRecord: PATCH with expected_version"]
  I --> K["deleteRecord: DELETE"]
  K -->|"409 has_dependents"| H
```

## Owner: ตรวจความเสี่ยง

```mermaid
flowchart LR
  O["/ overview"] --> RR["GET /v1/risk-report"]
  RR -->|"error"| X["Thai message: cannot reach accounts-api"]
  RR --> C["Totals per resource + counts per severity"]
  C --> F["Findings list, each links to /<resource>/<id>"]
  F --> FIX["Edit the record"]
```

Sources: `web/app/page.tsx`, `web/app/[resource]/page.tsx`, `web/app/[resource]/[id]/page.tsx`, `web/app/login/page.tsx`, `web/app/actions.ts`, `web/lib/auth-routes.ts`, `web/lib/auth.ts`, `web/lib/session.ts`, `web/lib/records.ts`, `web/lib/form.ts`

## Open questions
- Agent flows ผ่าน MCP ไม่มี UI; ดู `02-use-cases.md`
- lockout เก็บใน memory ต่อ warm instance (`auth-routes.ts` comment) — ยอมรับเป็น residual แล้วหรือไม่
