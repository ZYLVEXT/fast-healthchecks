# Contributing

## Project name

The canonical project name for documentation and UI is **Fast Healthchecks** (two words, with "s"). The PyPI package name is `fast-healthchecks`. Use this name consistently in these files (and any other project-facing text):

- README.md — main heading and project title
- docs/index.md — main heading and project title
- pyproject.toml — `description`
- zensical.toml — `site_name`

## Documentation (single source of truth)

Each piece of documentation has one canonical source. When editing, change only the canonical source; other files may contain a short pointer or link.

| Content | Canonical source |
|---------|------------------|
| Contributing guide | This file (CONTRIBUTING.md). docs/contributing.md includes it via Zensical. |
| Changelog | CHANGELOG.md. docs/changelog.md includes it. |
| Package version | pyproject.toml `version`. commitizen syncs to `fast_healthchecks/__init__.py` `__version__`. |
| Installation (pip/poetry/uv, extras) | docs/installation.md. README has a short line and link to the documentation. |
| Example code in docs | Files in `examples/`. Included in docs/usage.md via `include-markdown`. Code in `examples/` is part of the codebase and must follow PEP 8 and the project style (Ruff, pre-commit). |
| User-facing docs (configuration, lifecycle, probe options, DSN, run_probe, SSRF, PostgreSQL TLS rotation) | docs/ (docs/index.md and related Zensical pages). In case of conflict, docs are authoritative. README is the entry point with a short overview and links to the documentation. |
| Public API boundary (configs, to_dict) | **docs/api.md** is the single source of truth for the public API. README may have a one-line pointer to API Reference. |
| Style guide (naming, docstrings, standards) | This file. docs/style-guide.md is a pointer to the relevant sections. |
| Security policy | SECURITY.md (repo root). docs/security.md includes it for the documentation site. |
| Test certificates policy | This file, § Test certificates. README may have a one-line pointer. |
| Running tests (local) | README § Running tests. CONTRIBUTING § CI and release references it. |
| Task runner recipes (full list and descriptions) | justfile (and `just` or `just --list`). README lists only the main recipes with short pointers. |
| Doc structure (pages and order) | `nav` in zensical.toml. When adding or removing a page, update both `nav` and the link list in docs/index.md so they stay in sync. |

When adding or changing user-facing content, update the canonical source (docs or other as above); in README, add or keep only a short pointer or link if needed.

Wrapper pages in `docs/` (e.g. `docs/security.md`, `docs/changelog.md`, `docs/contributing.md`) that only include a file from the repo root must not duplicate the H1 heading from the included file; the H1 is defined once in the canonical source.

## Naming conventions

### Documentation files (docs/)

Use lowercase; multi-word filenames use a hyphen (e.g. `probe-options.md`, `dsn-formats.md`, `style-guide.md`). The repo root keeps `SECURITY.md` (uppercase) for GitHub convention; the documentation site uses `docs/security.md`, which includes it. The doc filename should match the key used in `nav` in zensical.toml (e.g. `Changelog: changelog.md`).

### Files and modules

- **Packages and modules:** Use `snake_case` (e.g. `fast_healthchecks`, `dsn_parsing`). See PEP 8.
- **Private modules:** Use a leading underscore for internal implementation modules (e.g. `_base`, `_imports`). These are not part of the stable public import surface. Config types are available from `fast_healthchecks.checks.configs`.
- **Tests:** Test files are named `test_*.py`. The pre-commit hook `name-tests-test` enforces this. Exceptions (utility or helper modules that are not tests) are listed in `.pre-commit-config.yaml` under that hook: `tests/utils.py` (shared test utilities), `tests/unit/integrations/helpers.py` (unit-test helpers), `tests/integration/checks/httpbin_like_app.py` (helper ASGI app for integration tests, not a test case).
- **Integrations:** FastStream and Litestar integrations intentionally duplicate the structure (health, _add_probe_route); shared logic lives in `integrations.base`.

### Workflows

Files in `.github/workflows/` use a numeric prefix for order. In the GitHub Actions UI, each workflow has a display name (`name:` in the file). Reference:

| File | Display name | Purpose |
|------|--------------|---------|
| `1_test.yml` | Tests | Pre-commit, import tests, unit tests, integration tests. |
| `2_bump.yml` | Bump version | Manual version bump and tag (commitizen). Optional input: `increment` (PATCH/MINOR/MAJOR). Release notes come from CHANGELOG.md; see below. |
| `2_rollback.yml` | Rollback release | Delete GitHub release and tag, force-push branch to commit before tag. |
| `3_release.yml` | Release | Build and publish to PyPI (Trusted Publishing). |
| `4_codeql.yml` | CodeQL | Code security analysis. |
| `5_dependency_review.yml` | Dependency review | Dependency review on pull requests. |

### Identifiers

- **Classes:** `PascalCase` (e.g. `HealthCheckResult`, `RedisHealthCheck`, `ProbeRouteOptions`).
- **Functions and methods:** `snake_case` (e.g. `healthcheck_safe`, `build_probe_route_options`, `run_probe`).
- **Module-level constants:** `UPPER_SNAKE_CASE` (e.g. `DEFAULT_HC_TIMEOUT`, `VALID_SECURITY_PROTOCOLS`, `REDACT_PLACEHOLDER`).
- **Private attributes and helpers:** Leading underscore (e.g. `_name`, `_config`, `_create_client`, `_get_check_name`). Exported names like `_CLIENT_CACHING_SLOTS` in `__all__` are intentional when subclasses need them (e.g. for `__slots__`).
- **TypeVars:** Single capital or suffix per PEP 484 (e.g. `T_co`, `ClientT`, `P`); use a leading underscore for module-internal TypeVars (e.g. `_T`). In TypedDict, camelCase for fields is acceptable when it matches an external API or driver (e.g. `authSource` for MongoDB).
- **Term in code:** Use the single word **healthcheck** in identifiers (e.g. `HealthcheckRouter`, `healthcheck_safe`). In prose (README, docs, docstrings) use "health check" or "health checks" (two words). When adding new public modules, add them to `docs/api.md`. When changing the public contract (new stable imports, deprecation, or removal), update the description in `docs/api.md` and the API note in README if present, so the public API boundary stays documented.

## Docstrings

Docstrings follow the **Google** convention. This is enforced by Ruff (`tool.ruff.lint.pydocstyle` in `pyproject.toml`). See [Google Python Style Guide — Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

**Module docstrings:** Use a single summary line (imperative or neutral, e.g. "Provide …", "Define …", or "Health check for X"). Add one or two lines of detail if needed. Optional sections such as Classes, Usage, or Example are acceptable for public modules that expose one main class; they are not required. New code and docstring refactors should follow this minimal template.

## Standards

The project follows:

- **PEP 8** — code style (enforced by Ruff).
- **PEP 257** — docstrings; **Google** convention for format (set in Ruff).
- **Semantic Versioning** — versioning (commitizen, semver in `pyproject.toml`).
- **Conventional Commits** — commit message format (commitizen check in pre-commit).
- **ADR** — architecture decisions in `docs/decisions/` with numbering and status. When adding a new ADR: create `docs/decisions/NNN-short-title.md` (e.g. `002-some-topic.md`), include sections Status, Context, and Decision; update the table in [docs/decisions/README.md](docs/decisions/README.md) with the new row (number, title, status, short summary).

## Backward compatibility and deprecation

- **SemVer:** We follow [Semantic Versioning](https://semver.org/). Version is MAJOR.MINOR.PATCH. Breaking changes require a MAJOR bump; new backward-compatible features use MINOR; backward-compatible fixes use PATCH. Breaking changes are recorded in CHANGELOG (under Refactor or a dedicated Breaking section) and trigger a MAJOR version bump. CHANGELOG and commitizen are aligned with this: each release entry is categorized (Feat, Fix, Refactor, etc.), and breaking changes are called out explicitly.
- **Stable surface:** What we guarantee across MINOR and PATCH releases are the symbols in `fast_healthchecks.__all__` and `fast_healthchecks.checks.__all__`, the documented public API in [docs/api.md](docs/api.md), and the behavior described there. The **supported public surface** (import paths and stability across minor versions) is that API reference and those `__all__` lists; see [docs/api.md](docs/api.md) for the full list. Subpackage import paths (e.g. `from fast_healthchecks.checks.redis import RedisHealthCheck`) that are documented or implied by the API reference are also stable unless deprecated.
- **Internal:** Modules or names not listed in the API reference or `__all__` (e.g. `_base`, `ToDictMixin.to_dict` on check instances) are internal. We may change or remove them without a MAJOR bump; avoid relying on them in production code.
- **Deprecation:** When we deprecate a public API, we (1) document the deprecation in CHANGELOG and in the relevant docstring or [docs/api.md](docs/api.md), (2) emit a `DeprecationWarning` at runtime where feasible (e.g. when the deprecated function or class is used), and (3) keep the deprecated API for at least one MINOR release before removal. Removal is done in a MAJOR release. The minimum timeline (one MINOR before removal) and this policy are documented here (CONTRIBUTING).

## CI and release

Full description of release and CI (workflows, secrets, bump, rollback, pre-commit) is only in this section. README has a short pointer and link here.

**Security:** Vulnerability reports are handled privately; see [SECURITY.md](SECURITY.md). Do not open public issues for security-sensitive bugs.

For running tests locally (`just tests-imports`, `just tests-unit`, `just tests-integration`, `just tests-all`), see README § Running tests.

### Bump workflow (how it works)

The Bump workflow (`2_bump.yml`) produces **one commit** per run. It uses commitizen to compute the next version (or the optional `increment` input: PATCH/MINOR/MAJOR).

- **If CHANGELOG.md has a `## Unreleased` section:** The workflow replaces only that section’s header with `## X.Y.Z (YYYY-MM-DD)` (body unchanged), runs commitizen to update version files only (no changelog generation), then commits CHANGELOG + version files in a single commit, creates the tag, and pushes. So the release notes are exactly what you wrote under `## Unreleased`.
- **If there is no `## Unreleased` section:** Commitizen runs with changelog generation enabled and commits the bump and generated changelog itself.

In both cases the GitHub Release body is the first version block from CHANGELOG.md after the bump. The project uses `update_changelog_on_bump = false` in `pyproject.toml`; the workflow enables changelog generation only when there is no custom Unreleased section.

### GitHub Actions secrets

- **Bump workflow (manual version bump):** Uses `PERSONAL_ACCESS_TOKEN` for checkout and commitizen-action (push version bump and tag). Use a Fine-grained PAT or GitHub App with minimal scope: repository **Contents** (read and write). No PyPI token is used for this workflow. Release notes for the GitHub Release are taken from the first version block in CHANGELOG.md after the bump (see § Bump workflow (how it works)).
- **PyPI publish:** Release is done via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC). The workflow uses `id-token: write` and `pypa/gh-action-pypi-publish`; no PyPI API token is stored in GitHub Secrets. Do not add a PyPI token to the `pypi` environment.

### Test certificates

Files under `tests/certs/` (e.g. `key.key`, `ca.key`) are used only to run tests (unit and integration, e.g. TLS checks). They are excluded from the pre-commit hook `detect-private-key` by design. Do not use them outside local or CI test runs. In production, use your own certificates and secrets.

### Reproducible build

On release (tag), the workflow runs a **reproducible-build** job: two builds in the same runner with the same Python version (3.14), same lockfile (`uv sync --frozen`), and `SOURCE_DATE_EPOCH=0`. Wheel hashes are compared; the job fails if they differ. **Scope:** reproducibility is defined within this fixed environment (same runner image, same Python patch version, same toolchain). We do not claim cross-version or cross-runner reproducibility.

### Pre-commit

Pre-commit runs the same checks as CI. The hook `no-commit-to-branch` is skipped on CI via `SKIP`. Pre-commit is executed with `uv run --no-sync pre-commit run ...`; `pre-commit-uv` is in the dev dependency group and locked in `uv.lock`.

When updating uv, update the uv-pre-commit revision in `.pre-commit-config.yaml` to match: use the [uv-pre-commit releases](https://github.com/astral-sh/uv-pre-commit/releases) and set `rev` to the commit SHA that corresponds to the uv version (keep the `# frozen: <version>` comment for readability).

Periodically update hook revisions in `.pre-commit-config.yaml` (e.g. run `pre-commit autoupdate`), then run pre-commit and the test suite to verify.
