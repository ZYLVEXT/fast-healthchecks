# Releasing

`fast-healthchecks` releases are produced from an already prepared clean commit. Privileged GitHub
workflows do not modify versions, changelogs, source files, or the lockfile.

## Repository configuration

Create protected GitHub environments named `release-operations`, `pypi`, and `github-pages`.
Require maintainer approval for `release-operations` and `pypi`, restrict them to the default branch
or release tags as appropriate, and configure the PyPI Trusted Publisher for
`.github/workflows/3_release.yml` with environment `pypi`.

Protect the default branch with `Tests / Required checks`, CodeQL, and dependency review. Enable
GitHub Pages through Actions and allow build provenance/SBOM attestations.

## Release flow

1. Update `pyproject.toml`, `fast_healthchecks/__init__.py`, `uv.lock`, and the first changelog entry
   to the same stable semantic version.
2. Run the complete Docker-backed matrix, documentation build, dependency audit, reproducible build,
   artifact smoke test, and final risk review locally.
3. Merge the clean release commit to the default branch.
4. Run `Tag prepared release` and approve the `release-operations` environment.

The workflow creates a draft release and dispatches Tests on the immutable tag. A release proceeds
only when the supplied Tests run proves the same workflow, tag, and commit. Artifacts are built
twice and compared, installed in isolation, accompanied by a deterministic CycloneDX SBOM, attested
by GitHub, published with PyPI Trusted Publishing, and attached to the release before documentation
and the GitHub Release become public.

Never force-push or delete a published release. Yank a faulty PyPI version and ship a corrected
version with a new tag.
