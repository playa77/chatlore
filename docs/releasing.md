# Release status for this fork

Install this fork from its Git checkout as described in the [README](../README.md).
The package is still named `chatlore`, versioned in `pyproject.toml` and
`src/chatlore/__init__.py`. The name alone does not identify this fork on PyPI.
No separate PyPI distribution or publisher for `playa77/chatlore` is established
by the repository's installation instructions.

## Existing workflow behavior

The inherited `.github/workflows/release.yml` triggers on `v*` tags. It builds a
wheel/source archive, checks the package version against the tag, runs the
inherited demo, then attempts trusted publishing to the PyPI project `chatlore`
through the GitHub environment `pypi`. A dependent job creates a GitHub release.
PyPI authorizes a publisher using its configured repository/workflow identity;
forking the repository does not inherit the upstream owner's publishing rights.

The separate Deploy workflow also responds to version tags when `HF_SPACE` is
configured. Release tags can therefore trigger more than a build. Do not use
the old upstream tag-and-publish procedure as a local installation step.

## Build locally without publishing

From this checkout:

```bash
uv build --out-dir dist
```

This builds this fork's files. It does not publish them. To check an artifact,
install the exact wheel into a separate test environment; do not test by
requesting a bare package name from PyPI, which selects the upstream package.
The bundled demo uses local embeddings, so it is not a remote-only acceptance
test. Normal local checks are in [CONTRIBUTING.md](../CONTRIBUTING.md).

## Before a future release

Choose and document the intended distribution name and publishing destination,
configure trusted publishing for this fork, and revise the Release/Deploy
workflows to match that decision. Decide whether a GitHub-only release is
sufficient. Keep original copyright and author attribution.

For a version change, update `pyproject.toml`, `src/chatlore/__init__.py`,
`uv.lock` and `CHANGELOG.md` together. Validate the built package and its actual
installation route before creating a release tag. Publishing and hosting are
outside the current local-only phase; no release action is performed here.
