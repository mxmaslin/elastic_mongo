# Agent context — Stream Catalog API

## Purpose

Showcase project for **MongoDB** and **Elasticsearch** proficiency (linked from the
author's resume). It must stay **production-shaped**: clean DDD layering, honest
trade-offs, green CI. Portfolio quality matters more than feature count.

Author: Maslin Maxim ([github.com/mxmaslin](https://github.com/mxmaslin)).
Resume workspace: `~/_job-search` (see its `AGENTS.md`).

## Architecture (enforced)

`api` (FastAPI) → `application` (services) → `domain` (aggregates, VOs, ports) ← `infrastructure` (Mongo/ES adapters).

- **domain** is pure Python: no framework, driver, or infrastructure imports.
- **application** talks to storage only through ports.
- MongoDB is the source of truth; Elasticsearch is a best-effort projection
  (retry/backoff in the adapter, `POST /v1/admin/reindex` as convergence).
- Optimistic concurrency via `version` field on both aggregates.
- Known trade-off (documented in README): dual-write instead of outbox/CDC — do
  not "fix" silently; it is called out on purpose.

## Quality gates (all must stay green)

```bash
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .
.venv/bin/python -m mypy                      # strict
.venv/bin/python -m pytest tests/unit -q      # no I/O
docker compose up -d mongo elasticsearch
.venv/bin/python -m pytest tests/integration -q
```

CI (GitHub Actions, `.github/workflows/ci.yml`): lint → unit → integration
(service containers) → docker build. Run gates locally before pushing.

## Conventions

- Conventional commits (feat/fix/chore/docs/refactor/test).
- Python 3.11, `src/` layout, strict typing.
- Integration tests use uuid-suffixed DB/index per session — never shared state.
- No auth by design (documented as out of scope in README) — do not add.
