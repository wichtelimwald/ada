# ReMe + LangMem: distribution-license review of five real findings

Status: **conditional / open for redistribution** (2026-09-23). This is a
research candidate assessment, not adoption, a license PASS, or legal advice.
The combined Mac run passed its behavioral checks and reported no known
`pip-audit` vulnerabilities; neither result clears distribution licenses.
The new `REVIEW-BUNDLE(20260923-144155).txt` reports versions, behavior, and
license metadata. The separately uploaded `license-paths(1).txt` adds paths
reconstructed from the combined installation and installed package file
lists. Neither upload supplies the full license/notice **contents**, a
redistributable release artifact, or license attribution for each native
library. Those must be checked before the project can close the gate in
`NOTICE.md`.

| Distribution in combined Mac run | License and route | Decision / remaining evidence |
| --- | --- | --- |
| `psycopg==3.3.6` | `LGPL-3.0-only`; in the reconstructed Ada baseline: `ada-assistant` → `dbos` → `psycopg`. | **Existing baseline obligation.** The installed package lists `licenses/LICENSE.txt`. Verify license contents, source availability, and the chosen distribution method. Do not attribute it solely to the memory candidates. |
| `psycopg-binary==3.3.6` | `LGPL-3.0-only`; reconstructed Ada route continues from `psycopg` → `psycopg-binary`. | **Existing baseline plus bundled-library review.** Its installed macOS file list includes `libpq`, `libssl`/`libcrypto`, Kerberos/GSSAPI, LDAP, and related `.dylib` files. Inspect their own licenses, notices, source and LGPL obligations in the exact wheel. Repeat for each release platform; this macOS installation does not clear a Linux container. |
| `bidict==0.24.1` | `MPL-2.0`; newly attributed in the installed graph to `reme-ai` → `agentscope` → `python-socketio` → `bidict`. | **Memory candidate addition.** The installed distribution lists a `LICENSE` file. If redistributed, review MPL-covered source and recipient access, including modifications if any. This does not relicense Ada-owned files. |
| `certifi==2026.7.22` | `MPL-2.0`; already reachable in the reconstructed Ada baseline through `pydantic-ai-slim` → `tiktoken` → `requests` → `certifi` (also reached through ReMe → `httpx`). | **Existing baseline obligation.** Its installed distribution lists a `LICENSE` file. Review actual wheel contents, certificate bundle, and any notice/source obligations before redistribution. |
| `orjson==3.12.0` | `MPL-2.0 AND (Apache-2.0 OR MIT)`; newly attributed in the installed graph to `langmem` → `langsmith` → `orjson`. | **Memory candidate addition, artifact review open.** The installed package lists three license files and a native `.so`; the package cannot be recorded as MIT-only. Inspect file-level licensing, notices, and MPL-covered source for the exact wheel before redistribution. |

The `BASELINE`/`NEW` distinction is computed from **combined-install metadata**
using Ada's declared requirements; no Ada-only environment was independently
installed. Paths establish dependency attribution, not actual runtime use or
redistribution compliance. File lists establish names, not the files' license
terms or bundled third-party source obligations.

The official [Psycopg binary documentation](https://www.psycopg.org/psycopg3/docs/api/pq.html)
confirms bundled native libraries. [Psycopg's package metadata](https://pypi.org/project/psycopg/3.3.6/),
[psycopg-binary's metadata](https://pypi.org/project/psycopg-binary/3.3.6/),
[bidict's metadata](https://pypi.org/project/bidict/0.24.1/),
[certifi's metadata](https://pypi.org/project/certifi/2026.7.22/), and
[orjson's license expression](https://github.com/ijl/orjson/blob/3.12.0/pyproject.toml)
identify the published licenses. See the [MPL 2.0 text](https://www.mozilla.org/en-US/MPL/2.0/)
and [LGPL 3.0 text](https://www.gnu.org/licenses/lgpl-3.0.html)
for the distribution obligations. Package metadata alone does not identify
every native library or prove that a proposed distribution complies.

## Exact-install attribution without repeating the full run

On the Mac with the already completed run, from the Ada checkout,
fetch the PR branch and extract this script into the ignored run artifacts.
This works even if the local checkout is on an older commit or another branch:

```sh
git fetch origin docs/adr-memory-architecture
git show FETCH_HEAD:research/memory/reme-langmem/license_paths.py \
  > artifacts/research/memory/reme-langmem/latest/license_paths.py
artifacts/research/memory/reme-langmem/latest/venv/bin/python \
  artifacts/research/memory/reme-langmem/latest/license_paths.py \
  artifacts/research/memory/reme-langmem/latest \
  > artifacts/research/memory/reme-langmem/latest/license-paths.txt
```

The script reads `inventory.json` and the five installed distributions'
`RECORD` file lists. It does not import candidate code or install packages.
It prints a dependency path from Ada and from the combined roots, the license
metadata, license/notice file names, and native library names. `BASELINE` is
reconstructed from Ada's requirements in the combined environment; it is not
an independently installed Ada-only environment. Direct install pins in the
research runner can also affect resolution. Upload `license-paths.txt` and,
if a route is missing or ambiguous, the existing `inventory.json` (package
names/requirements only; review before sharing). The script fails rather than
silently giving a partial graph when installed metadata is missing.

## Closure criteria for packaging or adoption

1. The five paths are traced for this combined installation. Recheck the
   baseline with an independent Ada-only install if the classification affects
   a distribution decision, and redo attribution when pinned versions change.
2. Inspect license and notice **contents**, not merely their filenames, plus
   binary/native files in the exact wheels for each intended target platform.
   Identify third-party libraries bundled in wheels and their distribution
   terms; determine source availability and LGPL/MPL compliance for the actual
   installation or container distribution method.
3. Record the explicit compatibility/distribution decision and necessary
   notice/source links in `NOTICE.md` for accepted components, including the
   existing DBOS chain. Escalate incompatible or unfulfillable obligations
   before adoption. Independently review the PR under the repository's
   four-eyes workflow.

There is no demonstrated incompatibility with MIT-owned Ada code at the
published metadata level. **The license hard gate remains open** until the
steps above are complete. A user installing wheels for personal research and
Ada redistributing those wheels in a container are different scenarios.
