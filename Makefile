.PHONY: install test lint format dev inspect generate demo clean

install:
	uv sync --extra dev

test:
	uv run pytest --cov=src/finance_mcp --cov-report=term-missing

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

format:
	uv run ruff format src/ tests/

dev:
	uv run fastmcp dev src/finance_mcp/server.py

inspect:
	uv run fastmcp inspect src/finance_mcp/server.py

generate:
	uv run python scripts/generate_dummy_data.py --output-dir sample_data/ --months 6 --seed 42

demo:
	uv run python scripts/setup_demo.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
