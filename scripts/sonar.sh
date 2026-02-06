#!/usr/bin/env bash
# Run SonarQube scanner with fallback env vars for local development.
# Usage: ./scripts/sonar.sh
# Or via pre-commit: pre-commit run sonar --all-files
# Requires: make tests-unit (or tests-all) first for coverage.xml

set -e

if [[ -z "${SONAR_ORGANIZATION}" ]]; then
  echo "Skipping SonarQube: SONAR_ORGANIZATION not set (required for SonarQube Cloud)"
  exit 0
fi

export SONAR_ORGANIZATION="${SONAR_ORGANIZATION}"
export SONAR_PROJECT_KEY="${SONAR_PROJECT_KEY:-fast-healthchecks}"
export CI_COMMIT_SHORT_SHA="${CI_COMMIT_SHORT_SHA:-$(git describe --tags --always 2>/dev/null || echo 'dev')}"

if [[ -f .coverage ]] && ! [[ -f coverage.xml ]]; then
  uv run coverage xml -o coverage.xml
fi

sonar-scanner -Dsonar.host.url="${SONAR_HOST}" -Dsonar.organization="${SONAR_ORGANIZATION}" -Dsonar.project.key="${SONAR_PROJECT_KEY}" -Dsonar.project.version="${CI_COMMIT_SHORT_SHA}"
