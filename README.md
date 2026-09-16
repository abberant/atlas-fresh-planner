# Atlas Fresh, Daily Apple Export Planner

Decision support workspace for the daily Production and Commercial meeting at Atlas Fresh.
Full documentation is written in milestone M6.

## Prerequisites

Python 3.11+, Node.js 20+, npm.

## Quick start

```
make setup    # python venv + backend deps, npm ci in frontend
make dev      # backend on :8000, frontend on :5173
make test     # backend tests
make build    # frontend production build
```

Without make:

```
python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
cd backend && .venv/bin/python -m pytest -q
```
