.PHONY: backend-install backend-lint backend-test backend-cov backend-run frontend-install frontend-run smoke

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

backend-lint:
	cd backend && . .venv/bin/activate && ruff check app tests

backend-test:
	cd backend && . .venv/bin/activate && pytest tests -q

backend-cov:
	cd backend && . .venv/bin/activate && pytest tests --cov=app --cov-report=term-missing -q

backend-run:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev

smoke:
	./scripts/smoke_backend.sh
