.PHONY: all lint check test build vendor-name-check

all: lint check vendor-name-check test

lint:
	uv run ruff check . --fix

check:
	uv run mypy src/ tests/ examples/

vendor-name-check:
	bash scripts/check_vendor_free_docs.sh

test:
	uv run pytest --cov=src/logseq_matryca_parser --cov-report=term-missing --cov-fail-under=80 -v tests/

build:
	uv run python -m nuitka --standalone --onefile src/logseq_matryca_parser/kinetic.py