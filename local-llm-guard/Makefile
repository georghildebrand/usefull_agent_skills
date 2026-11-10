.PHONY: install uninstall test check measure

install:
	uv sync
	claude mcp add --scope user local-llm-guard -- uv run --directory $(CURDIR) local-llm-guard

uninstall:
	claude mcp remove --scope user local-llm-guard

test:
	uv run pytest -q

check:
	uv run ruff check src tests
	uv run ruff format --check src tests
	scripts/check-confidentiality.sh

measure:
	uv run python scripts/measure.py
