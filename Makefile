# Atlas Fresh, Daily Apple Export Planner
# Raw commands for people without make are documented in README.md.
#
# Override the interpreter if your default python3 is not supported:
#   make setup PYTHON=python3.13

PYTHON ?= python3
VENV := backend/.venv
PIP := $(VENV)/bin/pip

.PHONY: check-python setup dev dev-backend dev-frontend test build start clean

check-python:
	@$(PYTHON) -c "import sys; v=sys.version_info; sys.exit(0 if (3,11) <= v[:2] <= (3,13) else 1)" \
	  || { \
	    echo ""; \
	    echo "  This project needs Python 3.11, 3.12 or 3.13."; \
	    echo "  Found: $$($(PYTHON) --version 2>&1) at $$(command -v $(PYTHON))"; \
	    echo ""; \
	    echo "  The pinned pydantic version has no prebuilt wheel for Python 3.14 or newer,"; \
	    echo "  so installing would try to compile it from source and fail."; \
	    echo ""; \
	    echo "  Point make at a supported interpreter, for example:"; \
	    echo "      make setup PYTHON=python3.13"; \
	    echo ""; \
	    exit 1; \
	  }
	@echo "Using $$($(PYTHON) --version 2>&1)"

setup: check-python
	$(PYTHON) -m venv $(VENV)
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
	rm -rf $(VENV) frontend/node_modules frontend/dist
