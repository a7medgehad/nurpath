.PHONY: backend-install backend-test backend-run frontend-install frontend-run fmt

backend-install:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e .[dev]

backend-test:
	cd backend && . .venv/bin/activate && pytest tests -q

backend-run:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend-install:
	cd frontend && npm install

frontend-run:
	cd frontend && npm run dev
