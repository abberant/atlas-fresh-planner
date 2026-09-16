# Atlas Fresh, Daily Apple Export Planner
# Raw commands for people without make are documented in README.md.

PY := backend/.venv/bin/python
PIP := backend/.venv/bin/pip

.PHONY: setup dev dev-backend dev-frontend test build start clean

setup:
	python3 -m venv backend/.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	cd frontend && npm ci

dev:
	@echo "Starting backend on :8000 and frontend on :5173 (Ctrl+C stops both)."
	@$(MAKE) -j2 dev-backend dev-frontend

dev-backend:
	cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/python -m pytest -q

build:
	cd frontend && npm run build

start: build
	cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000

clean:
	rm -rf backend/.venv frontend/node_modules frontend/dist
