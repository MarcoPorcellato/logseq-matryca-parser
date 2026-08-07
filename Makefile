.PHONY: all lint check test build vendor-name-check docs-check

all: lint check vendor-name-check docs-check test

lint:
	uv run ruff check . --fix

check:
	uv run mypy src/ tests/ examples/ scripts/check_documentation.py

vendor-name-check:
	bash scripts/check_vendor_free_docs.sh

test:
	uv run pytest --cov=src/logseq_matryca_parser --cov-report=term-missing --cov-fail-under=80 -v tests/

docs-check:
	uv run python scripts/check_documentation.py --root . --profile docs/maintained.toml --as-of-date $$(date -u +%F)

build:
	uv run python -m nuitka --standalone --onefile src/logseq_matryca_parser/kinetic.py
