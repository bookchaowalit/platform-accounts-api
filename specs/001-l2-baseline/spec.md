# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/platform-accounts-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** Both Railway services (`accounts-api`, `accounts-metadata-api`) installed unpinned dependencies with `pip install`, there was no type check, Ruff ran only the core rules with `ruff format` switched off, and the cell's own rules (trust zones, ciphertext-only mailboxes, per-platform handles, the risk report over stored rows) had no tests beyond the generic contract suite and the pure risk rules.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| Lock file and frozen install, CI caller bump, Ruff/mypy config and fixes, rule tests, `PRODUCT.md` | New endpoints or fields; schema changes |

## 3. Behaviour — scenarios

### AC-01 — Strictly isolated and unknown trust zones are refused

- **Given** an owner with write permission
- **When** they create an identity with `trust_zone` `z3-isolated` (or another unknown zone)
- **Then** the API answers 422; the four supported zones are accepted
- **Test:** `tests/test_identities.py::test_strictly_isolated_and_unknown_zones_are_refused` · level: unit / API with local fakes

### AC-02 — A slug is used once per workspace

- **Given** an identity `book` in the owner's workspace
- **When** the owner creates another `book`, and a second workspace creates `book`
- **Then** the owner gets 409 `conflict`; the other workspace gets 201
- **Test:** `tests/test_identities.py::test_a_slug_is_used_once_per_workspace` · level: unit / API with local fakes

### AC-03 — A plaintext address is never stored

- **Given** an identity
- **When** a mailbox arrives with an `@` in `address_ciphertext` or in `address_hash`
- **Then** the API answers 422 `invalid_value`
- **Test:** `tests/test_mailboxes.py::test_a_plaintext_address_in_the_ciphertext_is_refused` · level: unit / API with local fakes

### AC-04 — The same address hash is stored once per workspace

- **Given** a mailbox with a keyed hash
- **When** the same hash is created again in that workspace, then in another workspace
- **Then** 409 in the same workspace, 201 in the other
- **Test:** `tests/test_mailboxes.py::test_the_same_address_hash_is_stored_once_per_workspace` · level: unit / API with local fakes

### AC-05 — A handle is used once per platform

- **Given** an account `x:book`
- **When** `x:book` is created again and `youtube:book` is created
- **Then** 409 for the duplicate, 201 for the other platform
- **Test:** `tests/test_platform_accounts.py::test_a_handle_is_used_once_per_platform` · level: unit / API with local fakes

### AC-06 — The risk report reads only the caller's workspace

- **Given** a mailbox with SMS MFA in workspace A
- **When** an owner of workspace B asks for `/v1/risk-report`
- **Then** B sees no findings and zero totals
- **Test:** `tests/test_risk_report_route.py::test_the_report_reads_only_the_callers_workspace` · level: unit / API with local fakes

### AC-07 — The risk report needs read on every resource

- **Given** a caller with every permission except `accounts.mailbox:*`
- **When** they ask for `/v1/risk-report`
- **Then** the API answers 403
- **Test:** `tests/test_risk_report_route.py::test_read_permission_on_every_resource_is_required` · level: unit / API with local fakes

### AC-08 — The risk report never returns ciphertext or hashes

- **Given** a stored mailbox
- **When** the owner reads the report
- **Then** neither its `address_ciphertext` nor its `address_hash` appears; mailboxes are named by `address_hint`
- **Test:** `tests/test_risk_report_route.py::test_the_report_never_returns_ciphertext_or_hashes` · level: unit / API with local fakes

### AC-09 — A planned account is not reported until it is in use

- **Given** a `planned` account with SMS MFA
- **When** the owner reads the report, then stores an `active` one with SMS MFA
- **Then** only the active one gets `weak_mfa`
- **Test:** `tests/test_risk_report_route.py::test_a_planned_account_is_not_reported_until_it_is_in_use` · level: unit / API with local fakes

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `Dockerfile`, `services/accounts-metadata-api/Dockerfile` | changed | install from `uv.lock` with `uv sync --frozen --no-dev --no-editable`; same Python, user, CMD and copied files (the vendored service-auth now sits at its repository-relative path inside the image) |
| `.github/workflows/ci.yml` | changed | shared CI v1.1.1; `format-check` back on; coverage gates 58 (`accounts-api`) and 78 (`accounts-metadata-api`, measured 80.62%) |
| HTTP API | unchanged | no route, field or status code changed |

- **Data model / migration:** N/A — no schema change.
- **Backward compatibility:** same routes and payloads; only tooling, locks, typing fixes and tests changed unless a scenario above says otherwise.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Authorization unchanged; Sentry sends no PII and scrubs tokens/URLs | existing auth tests, Sentry tests |
| Reliability / observability | Reproducible install from the lock file; opt-in Sentry error reporting | image rehearsal before push; Sentry tests |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** unit and API tests with local fakes; no hosted service is called.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "58"` (measured 60.98% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_identities.py::test_strictly_isolated_and_unknown_zones_are_refused` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-02 | `tests/test_identities.py::test_a_slug_is_used_once_per_workspace` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-03 | `tests/test_mailboxes.py::test_a_plaintext_address_in_the_ciphertext_is_refused` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_mailboxes.py::test_the_same_address_hash_is_stored_once_per_workspace` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_platform_accounts.py::test_a_handle_is_used_once_per_platform` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_risk_report_route.py::test_the_report_reads_only_the_callers_workspace` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_risk_report_route.py::test_read_permission_on_every_resource_is_required` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_risk_report_route.py::test_the_report_never_returns_ciphertext_or_hashes` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-09 | `tests/test_risk_report_route.py::test_a_planned_account_is_not_reported_until_it_is_in_use` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |
| 2 | No test was red first: no behaviour bug was found; the new tests characterise existing rules. | — | owner | open |
| 3 | accounts-metadata-api: uv.lock with the vendored service-auth as a uv path source; strict mypy on server.py and _sentry.py; unittest under coverage.py (80.62%, gate 78). | — | owner | open |
| 4 | Ruff rule set in ruff.toml (it overrides pyproject [tool.ruff]); the vendored service-auth is excluded from Ruff so it stays byte-identical to bookchaowalit/platform-auth-sdk. | — | owner | open |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |

## Review (2026-10-24): changes requested

Checker: independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context). Status unchanged until fixed.

- Tests run by the checker: .venv/bin/pytest -q: 97 passed, 18 skipped
- Gap: All 9 ACs are tested, but §7 risk #1 (range rule may have left inverted rows) is template residue: no `ranges` in cell.yaml and §4 says no behaviour changed. Remove it.
