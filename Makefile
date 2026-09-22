# Countersign. Every target runs offline with no API keys.

VENV ?= .venv/Scripts
PY   := $(VENV)/python.exe

.PHONY: install corpus test lint fmt migrate check eval web serve deploy

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

## Measure everything against the ground truth; rewrites eval/results and eval/report.md.
eval:
	$(PY) -m eval.run

## Export console data and build the static site into web/out.
web:
	$(PY) -m scripts.export_web
	cd web && npm ci && npm run build

## Console and API together, as deployed: http://localhost:4321
serve:
	$(PY) -m scripts.serve_local

## Assemble deploy/ (console + API + snapshot) and ship it to production.
deploy: web
	$(PY) -m scripts.assemble_deploy
	cd deploy && vercel deploy --prod
