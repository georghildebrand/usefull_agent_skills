.PHONY: install uninstall test check measure

install:
	@echo "Task 5"

uninstall:
	@echo "Task 5"

test:
	uv run pytest -q

check:
	uv run ruff check src tests
	uv run ruff format --check src tests
	scripts/check-confidentiality.sh

measure:
	uv run python scripts/measure.py
