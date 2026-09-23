# Reproducible release input gate

**Status:** incomplete; release input gate fails until reviewed artifacts are committed.

Run `python3 scripts/check_release_inputs.py` before claiming a reproducible
source install or Ada-built image. It currently fails deliberately: there is
no reviewed Python 3.14 binary-wheel lock for macOS arm64, Linux amd64 and
Linux arm64, and `Dockerfile` uses a moving Python base-image tag.

For each target, resolve **all** runtime dependencies from `pyproject.toml`
at the final revision in an isolated Python 3.14 environment. Record the
platform, interpreter, package index, resolver version, resolution report,
exact wheel filenames and SHA256 values, including native bundled files.
Produce a separate `release-locks/requirements-<target>.txt` with every
direct and transitive package pinned to `==` and one or more independently
checked `--hash=sha256:...` entries. The `httpx2` direct pin in PR #28
must be present when that change is included. Re-resolve on dependency
changes; a Mac `pip freeze` lists installed versions but supplies neither
artifact hashes nor Linux-specific resolution.

Review and record the selected `python:3.14-slim` **manifest-list digest**
for both Linux architectures and the included Debian packages, then put
`FROM python:3.14-slim@sha256:<reviewed digest> AS base` in the Dockerfile.
Build both target architectures. Install wheels with
`pip install --require-hashes --only-binary=:all: -r <target lock>` and
verify that project build dependencies are pinned too; do not add a
hash-checked dependency install followed by a second unconstrained
`pip install /app`. Validate the complete image inventory and third-party
notices before distributing it.

The static gate checks formatting, direct-package presence and the base
reference. It does **not** resolve dependencies, validate hashes against
downloaded wheels, prove the selected wheels actually run, or clear
redistribution licenses. Keep this gate separate from normal local
development validation until the release inputs exist. No image or installer
is approved by this document.
