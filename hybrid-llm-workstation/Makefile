.PHONY: help venv install install-agent migrate seed control-dev worker-dev agent-dev \
        webui-up webui-down up down logs test test-control test-worker test-agent \
        test-integration lint gpu-smoke-test health backup restore

PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

CONTROL_PYTHONPATH := libs/core:.:apps/control/src
WORKER_PYTHONPATH := libs/core:.:worker/src
AGENT_PYTHONPATH := local-agent/src

help:
	@echo "Personal LLM Workstation — common targets:"
	@echo "  make venv               create .venv and install all Python deps"
	@echo "  make install-agent      install the local agent's minimal deps into .venv"
	@echo "  make migrate            apply database migrations (Alembic)"
	@echo "  make seed               create/update the admin user (WORKSTATION_ADMIN_PASSWORD required)"
	@echo "  make control-dev        run the control API with reload, on :8000"
	@echo "  make worker-dev         run one worker process"
	@echo "  make agent-dev          run the local execution agent, on :8787"
	@echo "  make up / make down     docker-compose up/down (control, worker, open-webui)"
	@echo "  make test               run the full automated test suite"
	@echo "  make health             run scripts/health checks against a running deployment"
	@echo "  make backup             export persistent state (see scripts/backup)"

venv:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt

install-agent:
	$(PIP) install -r local-agent/requirements.txt

migrate:
	$(VENV)/bin/alembic upgrade head

seed:
	PYTHONPATH=$(CONTROL_PYTHONPATH) $(PY) database/seeds/seed_admin.py

control-dev:
	PYTHONPATH=$(CONTROL_PYTHONPATH) $(VENV)/bin/uvicorn control.main:app --reload --host 0.0.0.0 --port 8000

worker-dev:
	PYTHONPATH=$(WORKER_PYTHONPATH) $(PY) -m worker.main

agent-dev:
	PYTHONPATH=$(AGENT_PYTHONPATH) $(VENV)/bin/uvicorn agent.main:app --reload --host 0.0.0.0 --port 8787

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

test:
	$(PY) -m pytest apps/control/tests worker/tests local-agent/tests tests -q

test-control:
	$(PY) -m pytest apps/control/tests -q

test-worker:
	$(PY) -m pytest worker/tests -q

test-agent:
	$(PY) -m pytest local-agent/tests -q

test-integration:
	$(PY) -m pytest tests/integration -q

lint:
	$(VENV)/bin/ruff check apps/control/src worker/src local-agent/src libs/core gpu

gpu-smoke-test:
	bash scripts/health/gpu_smoke_test.sh

health:
	bash scripts/health/check_all.sh

backup:
	PYTHONPATH=$(CONTROL_PYTHONPATH) $(PY) scripts/backup/export_state.py

restore:
	PYTHONPATH=$(CONTROL_PYTHONPATH) $(PY) scripts/backup/import_state.py $(FILE)
