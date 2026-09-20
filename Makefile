# Countersign. Every target runs offline with no API keys.

VENV ?= .venv/Scripts
PY   := $(VENV)/python.exe

.PHONY: install corpus test lint fmt migrate check

install:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

## Rebuild the synthetic corpus and its ground truth from the committed seed.
corpus:
	$(PY) -m data.generate

test:
	$(PY) -m pytest -q

lint:
	$(VENV)/ruff.exe check .
	$(VENV)/ruff.exe format --check .

fmt:
	$(VENV)/ruff.exe check . --fix
	$(VENV)/ruff.exe format .

migrate:
	$(VENV)/alembic.exe upgrade head

check: lint test migrate
	$(VENV)/alembic.exe check
