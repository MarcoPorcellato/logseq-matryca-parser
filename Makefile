.PHONY: all lint check test build

all: lint check test

lint:
	uv run ruff check . --fix

check:
	uv run mypy src/ tests/

test:
	uv run pytest -v tests/

build:
	uv run python -m nuitka --standalone --onefile src/logseq_matryca_parser/kinetic.py