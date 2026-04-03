.PHONY: help dev-up dev-down dev-restart prod-up prod-down prod-restart clean

include .env
export

DEV  = docker compose --env-file .env
PROD = docker compose --env-file .env.prod

help:
	@echo "WPP"
	@echo "==="
	@echo ""
	@echo "Dev:"
	@echo "  make dev-up        Start all services"
	@echo "  make dev-down      Stop all services"
	@echo "  make dev-restart   Restart all services"
	@echo ""
	@echo "Prod:"
	@echo "  make prod-up       Start all services"
	@echo "  make prod-down     Stop all services"
	@echo "  make prod-restart  Restart all services"
	@echo ""
	@echo "Other:"
	@echo "  make clean         Nuke containers, volumes, caches"
	@echo ""
	@echo "Ports:"
	@echo "  Frontend:  http://localhost:${FRONTEND_EXTERNAL_PORT}"
	@echo "  Backend:   http://localhost:${BACKEND_EXTERNAL_PORT}/docs"
	@echo "  Database:  localhost:${POSTGRES_EXTERNAL_PORT}"
	@echo "  Redis:     localhost:${REDIS_EXTERNAL_PORT}"

dev-up:
	$(DEV) up -d

dev-down:
	$(DEV) down

dev-restart:
	$(DEV) down
	$(DEV) up -d

prod-up:
	$(PROD) up -d

prod-down:
	$(PROD) down

prod-restart:
	$(PROD) down
	$(PROD) up -d

clean:
	$(DEV) down -v --remove-orphans
	docker builder prune -af
	docker image prune -af
