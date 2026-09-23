# ReMe + LangMem: distribution-license review of five real findings

Status: **conditional / open for redistribution** (2026-09-23). This is a
research candidate assessment, not adoption, a license PASS, or legal advice.
The combined Mac run passed its behavioral checks and reported no known
`pip-audit` vulnerabilities; neither result clears distribution licenses.
The recorded `REVIEW-BUNDLE.txt` reports versions and license metadata, but
does not contain the full dependency graph, installed wheel file lists, or a
redistributable release artifact. The exact installed artifacts must be
checked before the project can close the license gate in `NOTICE.md`.

| Distribution in combined Mac run | License and route | Decision / remaining evidence |
| --- | --- | --- |
| `psycopg==3.3.6` | `LGPL-3.0-only`; already required by adopted `dbos==3.0.0` through `psycopg[binary]` according to the research dependency analysis. | **Existing baseline obligation.** Verify the installed package's license text, source availability, and the chosen distribution method. Record this transitive obligation for DBOS too; do not attribute it solely to the memory candidates. |
| `psycopg-binary==3.3.6` | `LGPL-3.0-only`; optional compiled Psycopg implementation selected by the `binary` extra. | **Existing baseline obligation plus bundled-library review.** Psycopg documents that this variant includes required native libraries. Inventory the exact macOS arm64 wheel's native files and their own licenses, source/notice and LGPL linking requirements. Repeat for each release platform; a macOS wheel does not clear a Linux container. |
| `bidict==0.24.1` | `MPL-2.0`; preliminary route `reme-ai[as]` → `agentscope` → `python-socketio` → `bidict`. | **Memory candidate addition, pending graph confirmation.** If redistributed, preserve MPL-covered source and provide recipients a way to obtain it, including modifications if any. This does not relicense Ada-owned files. |
| `certifi==2026.7.22` | `MPL-2.0`; exact Ada baseline / candidate route **not yet established** by the uploaded bundle. | **Attribution open.** Trace its installed dependency path; review certificate bundle and license files in the actual wheel and source-availability notice for any redistribution. |
| `orjson==3.12.0` | `MPL-2.0 AND (Apache-2.0 OR MIT)`; exact Ada baseline / candidate route **not yet established** by the uploaded bundle. | **Attribution and artifact review open.** The package as a whole cannot be recorded as MIT-only. Inspect which files and native artifacts carry MPL versus Apache/MIT, preserve required notices and make MPL-covered source available when distributing a wheel. |

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

On the Mac with the already completed run, from the Ada checkout on this
branch, run:

```sh
artifacts/research/memory/reme-langmem/latest/venv/bin/python \
  research/memory/reme-langmem/license_paths.py \
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

1. Confirm all five exact dependency routes against the installed graph and
   distinguish already adopted DBOS transitive obligations from new additions.
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
