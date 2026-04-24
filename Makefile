.PHONY: test lint check all

test:
	pytest -v

lint:
	ruff check .

check:
	mypy src/ tests/ examples/

all: lint check test