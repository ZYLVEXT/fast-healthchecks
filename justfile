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

# Install pre-commit hooks. Run after uv sync --group=dev (or uv sync --all-extras --dev)
install-hooks:
    uv sync --group=dev
    pre-commit install
    pre-commit install --install-hooks

# Upgrade all uv dependencies
update-uv:
    uv sync --all-extras --upgrade

# Run linters (same as CI pre-commit job)
lint:
    uv run --no-sync pre-commit run --show-diff-on-failure --color=always --all-files

# ------------------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------------------

# Run import tests
tests-imports:
    uv sync --group=dev
    uv run pytest -p no:xdist --cov --cov-append -m 'imports' tests/unit/test_imports.py -vvv

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
    uv run pytest -p no:xdist --cov --cov-append -m 'integration' -W ignore::pytest.PytestUnraisableExceptionWarning -vvv

# Run unit tests
tests-unit:
    uv run pytest -n auto --cov --cov-append -m 'unit' -vvv

# Run all tests (imports, integration, unit) and print coverage
tests-all:
    rm -rf .coverage
    just tests-imports && just tests-integration && just tests-unit
    uv run coverage report

# ------------------------------------------------------------------------------
# Docs
# ------------------------------------------------------------------------------

# Serve documentation locally
serve-docs:
    uv sync --group=docs
    uv run zensical serve
