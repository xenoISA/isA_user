# Ruff Lint Baseline

> Authoritative description of the lint gate enforced on `core/` and
> `microservices/`. Source of truth: `pyproject.toml` at the repo root.
> Established by issue [#214](https://github.com/xenoISA/isA_user/issues/214).

## Why

Before #214 we had 862 raw Ruff findings across `core/` and
`microservices/`, including:

- 1 `F821` undefined-name (a real bug — `Event` was referenced without
  import in `authorization_service.py`'s role-assignment audit path)
- 47 `E722` bare `except:` clauses
- 6 `F403` star imports + 11 `F405` resulting undefined-local-with-import-star
- 581 `F401` unused imports

Cleaning the high-signal classes makes the lint gate meaningful again:
new `F821`/`E722`/`F403`/`F405`/`F401` regressions will be visible
instead of hidden inside the noise floor.

## What is enforced

`pyproject.toml` configures Ruff with:

- `select = ["E", "W", "F"]` — PEP 8 errors/warnings + pyflakes
- A small per-file ignore list for **intentional** patterns (see below)

Run locally:

```bash
ruff check core/ microservices/
```

CI runs the same command on every push and PR via `.github/workflows/ci.yml`'s
`lint` job. A clean run is the gate.

## Findings: before vs. after

| Rule | Description | Before | After |
|------|-------------|-------:|------:|
| `F821` | Undefined name | 1 | 0 |
| `E722` | Bare except | 47 | 0 |
| `F403` | Star import | 6 | 0 |
| `F405` | Undefined-local from star import | 11 | 0 |
| `F401` | Unused import | 430 | 0 |
| `F541` | f-string missing placeholders | 44 | 0 |
| `W291`/`W292`/`W293` | Trailing/missing-newline whitespace | 2005* | 0 |
| `E402` | Import not at top | 54 | 30 (ignored, see below) |
| `F841` | Unused variable | 41 | 36 (ignored, follow-up) |
| `E701`/`E702` | Multiple statements on one line | 21 | 21 (ignored, follow-up) |
| `F811` | Redefinition while unused | 2 | 2 (per-file ignore) |
| `F601` | Repeated dict key | 1 | 1 (per-file ignore) |

\* W2xx whitespace findings only become visible once `W` is enabled in
`select`; they were not counted in the original 658-finding inventory.

## Per-rule ignores

`pyproject.toml` ignores a few rules at the project level:

- `E501` line-too-long — Black handles formatting; long URLs/log strings exempted
- `E741` ambiguous variable name — legacy callsites, low signal
- `F841` unused-variable — 36 sites in service handlers where the assignment
  documents intent. **Tracked for follow-up** (re-enable once handlers are
  cleaned).
- `E701`/`E702` multiple statements per line — handful of legacy sites.
  **Tracked for follow-up.**

## Per-file ignores

These are *intentional* patterns where the linter is wrong:

| File pattern | Ignore | Reason |
|--------------|--------|--------|
| `microservices/*/clients/*.py` | `E402` | Service-to-service clients use `sys.path.insert(...)` before importing internal packages. The path manipulation MUST come before the import. |
| `microservices/payment_service/blockchain_integration.py` | `E402` | Layered file: helpers first, then a FastAPI `APIRouter` section that imports `fastapi` locally. |
| `microservices/campaign_service/campaign_repository.py` | `E402` | Same `sys.path` pattern as service clients. |
| `microservices/account_service/models.py` | `E402` | Late import of `role_validator` to avoid a circular import. |
| `microservices/billing_service/billing_repository.py` | `F811` | Duplicate `get_user_quotas` definition — tracked for follow-up. |
| `microservices/memory_service/episodic_service.py` | `F811` | Duplicate `vector_search` definition — tracked for follow-up. |
| `microservices/document_service/routes_registry.py` | `F601` | Duplicate `'GET /health'` route key — tracked for follow-up. |

## Extending the baseline

To add a new rule (e.g. `B` for flake8-bugbear):

1. Run `ruff check --select <RULE> core/ microservices/` to count findings.
2. If <50, fix them inline.
3. If 50–500, fix in a focused PR; add the rule to `select` only after the
   sweep lands.
4. If >500, add the rule to `select` *with* the noisiest files in
   `per-file-ignores`, then chip away across follow-up PRs.

To remove an ignore:

1. Drop the entry from `pyproject.toml`.
2. Run `ruff check --fix` to see what auto-fixes are available.
3. Hand-fix anything left, then commit.

## Out-of-scope cleanups

The following are **not** enforced by this baseline:

- Type checking (`mypy`) — runs in CI but `|| true`, so failures don't block.
- Black formatting on `core/` — Black currently runs on
  `microservices/` and `tests/` only.
- Import sorting (`I` ruleset / isort) — not enabled. A future sweep can
  introduce it.
- Bugbear (`B`), pyupgrade (`UP`), pep8-naming (`N`) — not enabled. These
  would each need a focused sweep first.
