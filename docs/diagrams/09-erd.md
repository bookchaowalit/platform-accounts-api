# 09 — ERD

Schema `accounts` บน Neon database `accounts` ทุก PK เป็น `(workspace_id, id)` และทุก FK รวม `workspace_id` (อ้างข้าม workspace ไม่ได้) ทุกตารางมี forced RLS `workspace_isolation`

```mermaid
erDiagram
  identities ||--o{ domains : "identity_id"
  identities ||--o{ mailboxes : "identity_id"
  identities ||--o{ accounts : "identity_id"
  domains ||--o{ mailboxes : "domain_id"
  mailboxes ||--o{ mailboxes : "recovery_mailbox_id"
  mailboxes ||--o{ mailboxes : "forwards_to_id"
  mailboxes ||--o{ accounts : "login_mailbox_id"
  accounts ||--o{ accounts : "admin_account_id"

  identities {
    uuid workspace_id PK
    bigint id PK
    bigint legacy_id
    text slug "unique per workspace"
    text display_name
    text trust_zone "z0-root z1-public z2-business z2-separated"
    text isolation_group
    text relation "self family work client"
    text status "planned active paused retired"
    text notes
    bigint version
    timestamptz created_at
    timestamptz updated_at
  }
  domains {
    uuid workspace_id PK
    bigint id PK
    bigint legacy_id
    text name "unique per workspace"
    bigint identity_id FK
    text registrar
    text dns_provider
    text mail_provider
    boolean auto_renew
    date renews_on
    text status "active parked releasing released"
    text notes
    bigint version
  }
  mailboxes {
    uuid workspace_id PK
    bigint id PK
    bigint legacy_id
    bigint identity_id FK
    bigint domain_id FK
    text address_ciphertext "no @ allowed"
    text address_hash "unique per workspace, no @"
    text address_hint
    text provider
    text kind "mailbox alias forward"
    bigint forwards_to_id FK
    bigint recovery_mailbox_id FK
    text mfa_method
    integer security_keys "0 to 20"
    boolean recovery_phone
    text status "active unverified dormant to-delete deleted"
    date last_reviewed_on
    text notes
    bigint version
  }
  accounts {
    uuid workspace_id PK
    bigint id PK
    bigint legacy_id
    bigint identity_id FK
    text platform
    text kind "profile page channel organization business service"
    text handle "unique with platform"
    text public_url
    bigint login_mailbox_id FK
    bigint admin_account_id FK
    text social_login "none google apple facebook other"
    text mfa_primary
    text mfa_backup
    boolean phone_bound
    text vault_ref
    text environment
    text status "planned setup active paused retired"
    date last_verified_on
    text notes
    bigint version
  }
  create_keys {
    uuid workspace_id PK
    uuid actor PK
    text kind PK
    text key PK
    bigint record_id
    timestamptz created_at
  }
  outbox {
    uuid id PK
    uuid workspace_id
    text type
    text subject
    uuid execution_id
    text classification
    jsonb payload
    timestamptz occurred_at
    timestamptz published_at
    integer attempts
    timestamptz next_attempt_at
    text last_error
    text correlation_id
  }
```

- `create_keys`: idempotent create (key จอง record id ก่อนเริ่ม platform execution)
- `outbox`: มีในทุก cell แต่ไม่มี resource ไหนประกาศ `graph` จึงว่าง (`docs/cellkit-notes.md`)
- `domains`, `accounts` ก็มี `created_at`/`updated_at` เหมือน `identities` (ละไว้ใน diagram)
- ข้อมูลอีกชุด: `accounts/ACCOUNT-MATRIX.yaml` (ไฟล์ใน Git, อ่านโดย `accounts-metadata-api`) ไม่ใช่ database

Sources: `migrations/0001_accounts.sql`, `migrations/0002_ciphertext_only.sql`, `cell.yaml`, `db/roles.sql`, `docs/cellkit-notes.md`, `services/accounts-metadata-api/service.yaml`

## Open questions
- ไม่มี
