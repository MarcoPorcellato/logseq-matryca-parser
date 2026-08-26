.PHONY: all lint lint-fix check test build vendor-name-check docs-check verify-clean ccp-plan ccp-doctor ccp-dry-run ccp-verify

all: lint check vendor-name-check docs-check test

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check . --fix

check:
	uv run mypy --cache-dir $${MYPY_CACHE_DIR:-.mypy_cache} src/ tests/ examples/ scripts/check_documentation.py scripts/check_release_contract.py scripts/check_wheel_contract.py scripts/generate_supply_chain_evidence.py scripts/update_compat_snapshots.py

vendor-name-check:
	bash scripts/check_vendor_free_docs.sh

test:
	uv run pytest --cov=src/logseq_matryca_parser --cov-report=term-missing --cov-fail-under=80 -v tests/

docs-check:
	uv run python scripts/check_documentation.py --root . --profile docs/maintained.toml --as-of-date $$(date -u +%F)

verify-clean:
	@status="$$(git status --porcelain)"; \
	if [ -n "$$status" ]; then \
		printf '%s\n' "$$status"; \
		exit 1; \
	fi

build:
	uv run python -m nuitka --standalone --onefile src/logseq_matryca_parser/kinetic.py

ccp-plan:
	bash scripts/run_qualified_ccp.sh plan --config .commit-ci-preflight.toml --json

ccp-doctor:
	bash scripts/run_qualified_ccp.sh doctor --config .commit-ci-preflight.toml --json

ccp-dry-run:
	bash scripts/run_qualified_ccp.sh dry-run --config .commit-ci-preflight.toml --json

ccp-verify:
	bash scripts/run_qualified_ccp.sh verify --receipt .ccp/receipt.json --policy .commit-ci-policy.toml --expected-commit "$$(git rev-parse HEAD)" --json
