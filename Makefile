.PHONY: all lint check test build

all: lint check test

lint:
	uv run ruff check . --fix

check:
	uv run mypy src/ tests/ examples/

test:
	uv run pytest --cov=src/logseq_matryca_parser --cov-report=term-missing --cov-fail-under=80 -v tests/

build:
	uv run python -m nuitka --standalone --onefile src/logseq_matryca_parser/kinetic.py