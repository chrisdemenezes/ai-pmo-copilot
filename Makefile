# STRATECH RC-2 -- reproducible local environment.
#
# PostgreSQL is the official development database from Wave 2 RC-2 onward
# (see docs/architecture/DECISION-LOG.md D-037 and
# docs/product/release-candidate/RC-2/). Every target below is idempotent
# and safe to re-run. Full walkthrough:
# docs/product/release-candidate/RC-2/Quick-Start.md
#
# Clone -> make setup -> make db-create -> make migrate -> make dev
# (make dev already depends on setup/db-create/migrate, so `make dev` alone
# is enough for a fresh clone.)

SHELL := /bin/bash
VENV_PY := .venv/bin/python
DATABASE_URL ?= postgresql://aipmo:aipmo@localhost:5432/aipmo

.PHONY: setup db-create migrate seed reset-db dev stop \
        test test-backend test-frontend test-e2e health

setup:
	@bash scripts/prepare-env.sh

db-create:
	@bash scripts/rc2-db.sh create

migrate:
	@DATABASE_URL="$(DATABASE_URL)" $(VENV_PY) -m alembic upgrade head

# Enterprise seed data (Organization, Users bootstrap on boot, Roles,
# Portfolio, Programs, Projects) is embedded in migrations 0002 + 0008 --
# `make seed` is an explicit alias for `make migrate` so the documented
# pipeline (clone -> setup -> db -> migrations -> seed -> ...) has a literal
# command at every step, without introducing a second, parallel seeding
# mechanism.
seed: migrate

reset-db:
	@bash scripts/rc2-db.sh reset
	@$(MAKE) migrate

dev: setup db-create migrate
	@DATABASE_URL="$(DATABASE_URL)" ./demo/start-demo.sh

stop:
	@./demo/stop-demo.sh

health:
	@curl -sf http://localhost:8000/health && echo || (echo "Backend not responding on :8000 -- is 'make dev' running?" && exit 1)

test: test-backend test-frontend
	@echo "Run 'make test-e2e' separately -- it starts its own dev server."

test-backend:
	@DATABASE_URL="$(DATABASE_URL)" $(VENV_PY) -m pytest

test-frontend:
	@cd web && npx vitest run

test-e2e:
	@cd web && npx playwright test
