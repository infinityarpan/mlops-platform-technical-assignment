.PHONY: up down test seed lint

up:
	docker compose up --build

down:
	docker compose down -v

seed:
	docker compose run --rm seed

backend-test:
	cd backend && python -m pytest

frontend-test:
	cd frontend && npx ng test --watch=false --browsers=ChromeHeadless

test: backend-test

lint:
	cd backend && python -m ruff check app tests
