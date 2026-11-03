# 11 — State machines

ทุก `status` เป็น enum ใน `cell.yaml` + CHECK constraint API **ไม่บังคับ transition** (PATCH ตั้งค่าใดก็ได้ใน enum) diagram ด้านล่างจึงแสดง **ค่าที่มีและความหมายที่ code ใช้** (เช่น risk report ถือว่า "live" สถานะไหน) ลูกศรแสดงลำดับที่ตั้งใจตามชื่อ ไม่ใช่กติกาที่ code บังคับ

## Account

```mermaid
stateDiagram-v2
  [*] --> planned : create (default)
  planned --> setup
  setup --> active
  active --> paused
  paused --> active
  active --> retired
  paused --> retired
  note right of planned : not live, ignored by risk report
  note right of active : live set = setup, active, paused
```

## Mailbox

```mermaid
stateDiagram-v2
  [*] --> active : create (default)
  active --> unverified
  unverified --> active
  active --> dormant
  dormant --> active
  dormant --> to_delete
  active --> to_delete
  to_delete --> deleted
  note right of dormant : live = active, unverified, dormant
  note right of to_delete : still counted for domain_release_takeover
```

## Domain

```mermaid
stateDiagram-v2
  [*] --> active : create (default)
  active --> parked
  parked --> active
  active --> releasing
  releasing --> released
  note right of releasing : releasing or released or auto_renew false with users = high finding
```

## Identity

```mermaid
stateDiagram-v2
  [*] --> active : create (default)
  [*] --> planned
  planned --> active
  active --> paused
  paused --> active
  active --> retired
```

(`to_delete` ใน diagram = ค่า `to-delete` จริง)

Sources: `cell.yaml`, `migrations/0001_accounts.sql`, `src/solo_accounts/routes.py` (`LIVE_MAILBOX`, `LIVE_ACCOUNT`, domain rules), `src/cellkit/app.py` (PATCH ไม่มี transition check)

## Open questions
- ควรบังคับ transition (เช่น ห้าม `deleted` → `active`) หรือไม่
