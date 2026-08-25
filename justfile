# fast_healthchecks – justfile
# macOS & Linux. Use: just [recipe]

default:
    #!/usr/bin/env sh
    echo "DEBUG_MODE: ${DEBUG_MODE:-}"
    echo ""
    just --list

# ------------------------------------------------------------------------------
# Common
# ------------------------------------------------------------------------------

# Activate project venv and start an interactive shell
bash:
    . .venv/bin/activate && exec "${SHELL:-sh}"

# ------------------------------------------------------------------------------
# Development
# ------------------------------------------------------------------------------

# Sync the full development environment and install coverage at interpreter startup.
setup:
    uv sync --frozen --all-extras --group dev --group docs
    @uv run python scripts/install_coverage_hook.py

# Install and prepare prek hooks. Run after uv sync --group=dev (or uv sync --all-extras --dev).
install-hooks:
    uv sync --group=dev
    uv run prek install --prepare-hooks

# Upgrade all uv dependencies
update-uv:
    uv sync --all-extras --upgrade

# Run all repository hooks, matching CI.
lint:
    uv run --no-sync prek run --show-diff-on-failure --color=always --all-files

# Validate immutable GitHub Action and Docker image references.
pin-check:
    uv run --no-sync python scripts/validate_dependency_pins.py

# Forbid checks and execution from importing integrations.
lint-imports:
    uv run --no-sync lint-imports

# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------

# Run import tests
tests-imports:
    uv sync --group=dev
    uv run pytest -p no:xdist --cov --cov-append --cov-fail-under=0 -m 'imports' tests/unit/test_imports.py -vvv

# Run integration tests. Set DOCKER_SERVICES_UP=1 to skip compose up/down
tests-integration:
    #!/usr/bin/env sh
    set -e
    cleanup() {
      if [ "${DOCKER_SERVICES_UP}" != "1" ]; then
        echo "Stopping services..."
        docker compose down --remove-orphans --volumes
      fi
    }
    trap cleanup EXIT
    if [ "${DOCKER_SERVICES_UP}" != "1" ]; then
      docker compose up -d --wait
    fi
    uv sync --group=dev --all-extras
    uv run pytest -p no:xdist --cov --cov-append --cov-fail-under=0 -m 'integration' -W ignore::pytest.PytestUnraisableExceptionWarning -vvv

# Run unit tests
tests-unit:
    uv run pytest -n auto --maxprocesses=8 --cov --cov-append --cov-fail-under=0 -m 'unit' -vvv

# Run all tests (imports, integration, unit) and print coverage
tests-all:
    uv run coverage erase
    just tests-imports && just tests-integration && just tests-unit
    uv run coverage report --fail-under=100

# Run the unit and import suites without Docker.
tests-fast:
    uv run coverage erase
    uv run pytest -n auto --maxprocesses=8 --cov --cov-report=term-missing --cov-fail-under=0 -m 'unit'

# ------------------------------------------------------------------------------
# Docs
# ------------------------------------------------------------------------------

# Serve documentation locally
serve-docs:
    uv sync --group=docs
    uv run zensical serve

# Build documentation.
docs-build:
    uv sync --frozen --group=docs
    uv run zensical build

# Build source and wheel distributions.
build:
    uv build
