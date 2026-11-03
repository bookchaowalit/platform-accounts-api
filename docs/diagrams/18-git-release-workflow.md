# 18 — Git / release workflow

ข้อเท็จจริงจาก history: PR #1–#8 merged ระหว่าง 2026-10-17 ถึง 2026-10-18 (ส่วนใหญ่ merge ภายใน 1–6 นาที, #1 29 นาที); หลังจากนั้นเป็น direct push ลง `main` (main-only ตาม SPEC-001 "committed straight to `main`") และ merge commit ของ PR #7/#8 (`a762ad9`, `64cb485`) `main` ไม่มี branch protection

```mermaid
gitGraph
  commit id: "8b36b95 PR1 squash"
  commit id: "9d8a716 PR2 squash"
  commit id: "511ef8e PR3"
  commit id: "2b9968e PR4"
  commit id: "a1862f1 PR5"
  commit id: "3d60707 PR6"
  branch docs-cd
  commit id: "128136a"
  checkout main
  merge docs-cd id: "a762ad9 merge PR7"
  branch chore-iac
  commit id: "0e8b4f2"
  checkout main
  merge chore-iac id: "64cb485 merge PR8"
  commit id: "e2f1c4d L2 baseline"
  commit id: "0ce3047 red test"
  commit id: "78fa510 fix"
  commit id: "d55fee3 docs"
  commit id: "b2d25b9 next bump"
  commit id: "e7de6ce SPEC review"
```

```mermaid
flowchart LR
  A["Work locally or on short branch"] --> B["Local checks: pytest, mypy, ruff (AGENTS.md)"]
  B --> C{"PR or direct push to main"}
  C --> D["CI on main"]
  D -->|"green"| E["Railway Wait for CI deploys both services"]
  D -->|"red"| F["No deploy"]
  E --> G["Verify /health and one authorized read (AGENTS.md)"]
  H["web/ change"] --> I["vercel deploy --prod (manual)"]
```

Sources: `git log origin/main`, `gh pr list --state merged` (2026-11-04), `gh api .../branches/main/protection` (404), `AGENTS.md`, `README.md`, `specs/001-l2-baseline/spec.md`, `.railway/railway.ts`

## Open questions
- ไม่มี tag/release — version ใช้ commit SHA เท่านั้น
- PR #1–#6 เป็น squash merge (commit เดียวบน `main`); #7 และ #8 เป็น merge commit
