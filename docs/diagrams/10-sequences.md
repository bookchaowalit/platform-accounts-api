# 10 — Sequences

## 1. Create mailbox จาก web (write path พร้อม execution)

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser
  participant W as solo-accounts-web (server action)
  participant A as accounts-api
  participant P as empire-platform
  participant D as Neon accounts DB
  B->>W: submit form (address in clear, over HTTPS)
  W->>W: requireSession, encryptAddress + hashAddress + addressHint
  W->>A: POST /v1/mailboxes, Bearer accounts-web, Idempotency-Key
  A->>A: verify RS256 token, bind workspace
  A->>P: POST /v1/authz/decide (accounts.mailbox:write precheck)
  P-->>A: allow
  A->>D: BEGIN, set app.workspace_id
  A->>D: reserve: INSERT create_keys with nextval id (or reuse existing key)
  A->>D: INSERT mailbox, reserved id when keyed, RETURNING row
  A->>P: POST /v1/executions (permission, record id, idempotency key, correlation id)
  P-->>A: execution id
  A->>D: COMMIT
  A->>P: POST /v1/executions/{id}/finish (before_hash, after_hash)
  A-->>W: 201 record (ciphertext only)
  W-->>B: revalidate list
```

## 2. Risk report

```mermaid
sequenceDiagram
  autonumber
  participant W as web overview page
  participant A as accounts-api
  participant P as empire-platform
  participant D as Neon
  W->>A: GET /v1/risk-report
  loop identity, domain, mailbox, account
    A->>P: POST /v1/authz/decide (accounts.<resource>:read)
  end
  A->>D: SELECT fixed columns ORDER BY id LIMIT 20001 (per resource, under RLS)
  alt more than 20000 rows
    A-->>W: 413 workspace_too_large
  else
    A->>A: analyse() into findings, sort by severity
    A-->>W: counts, findings (max 1000), truncated, totals
  end
```

## 3. Password sign-in

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser
  participant W as /auth/password
  B->>W: POST password + code
  W->>W: guardRequest (origin, content type)
  W->>W: check lockout map (5 failures, 15 min)
  W->>W: checkPasswordLogin (scrypt + TOTP)
  alt wrong
    W-->>B: wait 600 ms, 303 /login?error=password
  else right
    W->>W: createSession (sealed, 8 h, generation)
    W-->>B: 303 / with __Host-accounts-session
  end
```

## 4. Solo Web reads the account matrix

```mermaid
sequenceDiagram
  autonumber
  participant S as Solo Web
  participant M as accounts-metadata-api
  participant F as ACCOUNT-MATRIX.yaml (in image)
  S->>M: GET /api/v1/accounts?status=&platform=&kind=&q= with service JWT
  M->>M: check_read_auth (RS256, audience accounts-api, scope accounts:read)
  M->>F: MatrixStore.snapshot()
  M-->>S: projected rows, anonymous identities as counts only
```

Sources: `web/app/actions.ts`, `web/lib/form.ts`, `web/lib/crypto.ts`, `web/lib/api.ts`, `web/lib/auth-routes.ts`, `web/lib/password.ts`, `web/app/page.tsx`, `src/cellkit/app.py`, `src/cellkit/platform.py`, `src/solo_accounts/routes.py`, `services/accounts-metadata-api/server.py`, `services/accounts-metadata-api/Dockerfile`

## Open questions
- ไม่มี (ลำดับ reserve → INSERT อ่านจาก `src/cellkit/app.py` `reserve()` และ create handler)
