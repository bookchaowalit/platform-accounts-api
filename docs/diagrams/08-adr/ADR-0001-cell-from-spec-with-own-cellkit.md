# ADR-0001 — Cell สร้างจาก `cell.yaml` และ repo เป็นเจ้าของ `cellkit` เอง

- Status: accepted (retro-documented)
- Date of evidence: 2026-10-12 (generator retired), 2026-10-21 (owner decision, per `docs/cellkit-notes.md`)

## Context
ต้องการ API CRUD 4 resource ที่มีกติกาเหมือนกันทุก resource (filters, idempotency, version, audit) และ route เฉพาะ cell หนึ่งตัว (risk report)

## Decision
- Resource, field, enum, unique, filter ประกาศใน `cell.yaml`; `cellkit.app.create_app` สร้าง route และ Pydantic model จาก spec
- Custom route ผ่าน `extend: solo_accounts.routes:register`
- `src/cellkit/` เป็น code ของ repo นี้ ไม่ sync จาก upstream (generator `solo-cell-kit` retired 2026-10-12)
- Python FastAPI + psycopg + uvicorn; lock ด้วย `uv.lock` และ `uv sync --frozen`

## Consequences
- แก้ framework ได้ในที่เดียวพร้อม contract test (`src/cellkit/contract.py`)
- copy นี้อาจ drift จาก cell อื่น (ยอมรับแล้วใน cellkit-notes)

Evidence: `cell.yaml`, `src/cellkit/app.py`, `src/cellkit/spec.py`, `AGENTS.md`, `docs/cellkit-notes.md`, `pyproject.toml`, `Dockerfile`, `uv.lock`
