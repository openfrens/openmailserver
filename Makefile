.PHONY: install test lint run

install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e ".[dev]"

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .

run:
	.venv/bin/uvicorn openmailserver.app:app --reload --host 0.0.0.0 --port 8787
