.PHONY: run lint test docker-build docker-up docker-down

run:
	python -m src.main

lint:
	ruff check src/
	ruff format --check src/

lint-fix:
	ruff check --fix src/
	ruff format src/

test:
	pytest tests/ -v

docker-build:
	cd docker && docker compose build

docker-up:
	cd docker && docker compose up -d

docker-down:
	cd docker && docker compose down

docker-logs:
	cd docker && docker compose logs -f bot

db-shell:
	docker exec -it docker-db-1 psql -U bot -d pushover
