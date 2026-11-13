# KDBX reader for Ada — experimental compatibility gate

**Date:** 2026-11-13  
**Status:** PoC only — no real credentials, no production library approval.

## Requirement and threat boundary

One encrypted Ada-only KDBX file under the configured persistent Memory
storage root (`secrets/ada.kdbx`), read by the container after a human
passphrase prompt. No Keychain/1Password access, no automatic unlock, no
password in argv/env/logs, no model-facing secret tool. The vault is not
semantic Memory and is excluded from Git history and retrieval.

The PoC provides both a one-shot **unlock then lock** command and an opt-in **in-process** local-chat unlock for the lifetime of that chat. It does not unlock a separate already-running application process, expose credentials to an authorized calendar/mail consumer, or provide live IONOS integration.

## Reader alternatives and license gate

| Option | Evidence | Assessment |
| --- | --- | --- |
| PyKeePass 4.2.0 | Python KDBX3/4 reader; GPL-3.0 ([PyPI](https://pypi.org/project/pykeepass/)) | Mature relative to new alternatives; adding this Python runtime library risks copyleft obligations when distributing Ada under MIT. Not selected. |
| KeePassXC CLI | Native CLI, GPLv3; KDBX support ([official documentation](https://keepassxc.org/docs/KeePassXC_UserGuide)) | Independent binary/process possible, but additional Linux/Qt packages and IPC/per-call passphrase handling. Reserve fallback if the Python option fails. Requires separate artifact-level distribution review. |
| kdbxtool 0.1.7 | Python >=3.12, Apache-2.0, KDBX4/Argon2; [PyPI](https://pypi.org/project/kdbxtool/), [source](https://github.com/coreyleavitt/kdbxtool) | **Opt-in PoC reader only.** No GPL linking. Alpha, single maintainer, minimal adoption. A maintainer-reported Docker/KeePassXC smoke test and exact-head Python 3.14 tests now pass; production security and supply-chain approval remain open. |
| kdbxweb 2.1.1 | MIT, JS, KDBX4; external Argon2 implementation needed ([npm](https://www.npmjs.com/package/kdbxweb)) | Would add Node.js and an Argon2 integration only for secrets; disproportionate for Python Ada. |
| Custom KDBX parser | No dependency | Reimplementing authenticated encryption/KDF/XML handling is unnecessary security risk. Rejected. |

**Transitive scope (kdbxtool PoC):** `argon2-cffi`,
`pycryptodomex`, `defusedxml` and their resolved dependencies. No native
Ada-built images or installers are published. Exact dependency graph,
installed Linux wheels, license notices, and Python 3.14 availability must
be verified before publishing/bundling. The optional extra pins only the
top-level reader, not every transitive wheel. Never call this a cleared
production dependency gate.

## Focused PoC / pass-fail gates

- `docker build --target secrets-poc`: the maintainer reports building/running the optional reader on Python 3.14 Linux; the exact image digest was not captured.
- `ada secrets-check --memory-root ...` on an interactive Docker terminal: the maintainer reported successfully opening a genuine KeePassXC file and rejecting a wrong passphrase. The built image digest was not recorded; this is **operator-reported smoke evidence**, not an audited security test.
- Non-interactive invocation refuses to prompt; restart prompts again
  rather than retaining a decryption token.
- A secret reference not in the trusted allowlist is denied by the adapter;
  missing/duplicate entries fail closed. Unit tests use synthetic fake DB.
- Git Memory history never stages `secrets/`; regular manual `git add -A`
  excludes it; forced addition is detected and refused on next Memory init.
  **Manual `git add -f` can still force a secret into history and cannot be
  undone by ignore rules.** Operators must review backups/sync and history.
- No secret access tool is passed to the model and there is no DBOS credential consumer in this PoC. Live calendar wiring and complete trusted authorization are **not implemented**. The optional `ada chat --unlock-vault` is implemented as **same-process** vault lifetime only; its VS Code profile is **synthetic-only**.

## Independent review findings and prerequisites for real credentials

The independent agent review at [PR #57](https://github.com/wichtelimwald/ada/pull/57#pullrequestreview-5897060313) reproduced same-UID memory exposure in Docker Desktop: an unrelated process could read the KDBX master passphrase and plaintext entries from an unlocked Python process. The passphrase can decrypt every accessible backup. `kdbxtool.zeroize_credentials()` does not reliably erase immutable Python strings or the original key bytes; `lock()` must not be described as memory erasure. The VS Code Dev Container runs other same-UID processes with network access. **No real secrets in this PoC.**

Before any real credentials: **isolate the credential process from startup**, with no other same-UID workloads in its PID namespace and no `docker exec` during unlock. The Linux `PR_SET_DUMPABLE=0` guard prevents *new* same-UID process-memory opens, but is bypassed by file descriptors opened before the guard (PR #59 review B1). Test both an early, pre-opening sibling and a late opener on the actual runtime, and fail closed unless isolation is established. Discard reader-held passphrase/key references immediately after opening, reject weak KDFs before derivation, bound Argon2 work, fully review and hash-lock the dependencies actually executed in the credential process, and audit the reader. Also enforce a runtime memory limit to contain unbounded but authenticated gzip expansion. Python immutable-string remnants, the process's own code, and host privileges remain outside this guarantee. The remaining parent-directory path race is an operator-controlled boundary.

Evidence: maintainer-reported `17/17` focused tests and `333/333` full tests at commit `c3762db30030814e8499d1ffef3ebeab88217421` in Python 3.14.10/Linux ARM64. No CI attestation, independent human review or production-credential validation.

## Security hardening in progress (issue #58)

The follow-up branch adds a **fail-closed Linux process gate**:
`PR_SET_DUMPABLE=0` is applied before the terminal asks for a passphrase.
Direct adapter access also checks `PR_GET_DUMPABLE == 0`. The selected
reader now reads from one `O_NOFOLLOW` file descriptor and checks the
unauthenticated KDBX header **before** deriving a key.

**Current hardening branch (issue #58 / PR #60):** KDBX4 with
Argon2d or Argon2id, **64–256 MiB**, **3–128 iterations** and **1–8
parallel lanes**, with a combined `memory_kib × iterations` ceiling
of **8,388,608 KiB-rounds (8,192 MiB-rounds)**. The strict isolated
credential image additionally requires **at least 2,097,152 KiB-rounds
(2,048 MiB-rounds)**; the synthetic research mode keeps its legacy test
compatibility. Legacy AES-KDF, weak strict KDFs and out-of-budget
requests fail closed **before derivation**. These numeric thresholds
still require target benchmark and independent review. This replaces
the 10-iteration ceiling from merged PR #59.

**Why:** KeePassXC 2.8.0 targets ~1 second by calibrating a vault's
Argon2 rounds; the reviewer's 64 MiB / 4-lane target-Virtual-Machine
measurement estimated ~51 iterations. That setting now passes header
preflight without relaxing the minimum memory/iteration checks. This
does **not** establish a universal one-second runtime budget: Argon2
costs vary with hardware, lanes, and workload. Before live credentials
verify an *actual KeePassXC 2.8.0 synthetic vault* and worst-case
derivation in the bounded container. Do not weaken a real vault's KDF
to fit these bounds.

The adapter calls `zeroize_credentials()` **immediately** after decrypting,
releasing the reader's stored password/key references. This remains *reference
release*, **not reliable Python memory zeroization**; decrypted entry strings
still live for the unlocked session. Exact-head Linux/aarch64 tests confirmed
`PR_SET_DUMPABLE=0` and **late-opening** sibling denial. The independent
review on `5fb62bb` reproduced the missing case: a pre-existing same-UID
process opened `/proc/<pid>/mem` **before** `prctl` and read the master
passphrase during unlock and decrypted entries afterwards (5/5 each).
Dumpability is checked at descriptor-open time; an already-open descriptor
remains readable. Dedicated isolation **from startup**, not just `prctl`,
is mandatory before real credentials.

**Target-specific KDBX subset is now hash-locked (not full Ada):**
The maintainer ran `scripts/capture_kdbx_wheel_hashes.py` in CPython 3.14 /
Linux aarch64. Its pip report resolved precisely seven KDBX packages and
`--require-hashes --dry-run` completed successfully. The exact reported
wheel hashes are committed as
[`requirements/kdbx-py314-linux-aarch64.txt`](../../requirements/kdbx-py314-linux-aarch64.txt).
The opt-in `secrets-poc` Docker stage and VS Code KDBX research profile now
install this subset with `--require-hashes --only-binary=:all:` and
`--force-reinstall`; no downloaded source distributions are permitted.
The rest of Ada and the floating `python:3.14-slim` base image are **not**
locked by this file; this remains a **synthetic-only** dependency boundary.

The maintainer's terminal output showed successful resolution of the seven
wheel hashes, and the independent PR #59 reviewer matched each hash to
an official non-yanked PyPI wheel. The hash-locked `secrets-poc` Docker build
succeeded on exact head `5fb62bb`; the **VS Code Dev Container post-create
install** is still untested. The reviewer also counted **43 additional
unhashed runtime packages** in that image (plus its build dependency):
this KDBX-only lock is **not** a complete credential-process supply-chain
gate. The capture tool prints a candidate without leaving untracked files.
See `NOTICE.md` for provisional license metadata and distribution blockers.

**Still prohibited:** real credentials. The default/shared VS Code runtime is
not a production credential environment. Reviewed hash-pinned transitive
dependencies, reader audit, dedicated runtime isolation and an independent
security re-review remain uncompleted. See [issue #58](https://github.com/wichtelimwald/ada/issues/58).

## Reader source-inspection notes (not a completed audit)

Inspected the exact tagged upstream source `coreyleavitt/kdbxtool@v0.1.7`:

- `Kdbx4Reader.decrypt` verifies the header SHA-256, derived-key header HMAC,
  and per-block HMACs using `constant_time_compare` before decrypting the
  XML payload. This is a positive static observation; it is **not** a
  cryptographic correctness proof.
- `Database.open_bytes` retains ordinary Python `_password` and
  `_transformed_key` fields, confirming the earlier review's finding.
  Our read-only Ada wrapper releases these references immediately after open.
- **Verified unbounded expansion, post-authentication only (PR #59 I2):**
  `Kdbx4Reader.decrypt` verifies the header HMAC and all encrypted-block
  HMACs **before** decrypting and calling unbounded `gzip.decompress`.
  The reviewer opened an authenticated 65 KiB synthetic vault expanding
  to 64 MiB (approximately 1004:1); peak RSS rose to about 224 MiB versus
  94 MiB for a baseline vault. Ada's 16 MiB encrypted-file limit does
  **not** bound decompressed XML (theoretical expansion on the order of
  16 GiB). A malicious crafted vault requires a party who already knows
  the passphrase; no pre-authentication gzip attack path was found.
  The practical remaining risk is process/container OOM from an
  oversized but password-authorized vault. Run the credential process
  under a Docker `--memory` cap and verify OOM containment before real use.

A targeted independent reader review remains mandatory before using any real
credentials, including payload-size behavior and verification that no
authenticated content is parsed before cryptographic checks.

## Follow-up review verification (PR #59, exact head `5fb62bb`)

The independent agent's [second review](https://github.com/wichtelimwald/ada/pull/59) reported **FIX** on
the reviewed revision, with eight inline findings. The reviewer ran the
**full validation** in the development image: **344 tests discovered,
6 skipped** (optional KDBX reader absent), `ada doctor` OK. In the
hash-locked `secrets-poc` image: **27/28** focused tests passed; the
one failure was the missing **Git CLI** needed by
`test_memory_git_does_not_stage_vault_even_with_add_all`, which passed
in the development image. These were two distinct test environments,
not a single fully green container. There is no CI attestation.

B1 reproduced a same-UID process that pre-opened `/proc/<pid>/mem`
before `prctl` and could read the master passphrase during unlock and
a decrypted entry afterward. This contradicts the earlier interpretation
of `PR_SET_DUMPABLE=0` as sufficient same-UID isolation. The current
documentation and test naming distinguish **late-open protection**
from the still-unmet **isolated-from-startup** requirement.

The review also independently matched all seven KDBX SHA-256 digests
to official, non-yanked PyPI wheels. The remaining **43 distributions**
in the experimental image are not covered by those hashes, and the
application/build chain needs an end-to-end integrity review before
live credentials. The exact Docker image build and focused tests reported
by the maintainer were successful on `5fb62bb`.
Changes after that revision are documentation and test naming only.

## Decision

The project accepts **KDBX vault format + manual unlock** (ADR-0013).
It does **not** yet accept `kdbxtool` as production runtime library.
Prefer re-evaluating KeePassXC CLI over custom crypto if maturity/interop
checks on kdbxtool fail.
