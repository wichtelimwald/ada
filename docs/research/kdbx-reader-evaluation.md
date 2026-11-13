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

Before any real credentials: set `PR_SET_DUMPABLE=0` on Linux before the prompt and verify it fails closed on unsupported environments; discard the reader's stored passphrase/key material immediately after opening; reject weak AES-KDF/Argon2 parameters **before** expensive derivation; enforce a maximum KDF resource budget; hash-pin a reviewed transitive dependency set; re-review the reader's KDBX read path; isolate the actual credential runtime from development tools/extensions and unnecessary egress. A residual process-compromise and immutable-string memory risk remains even then. TOCTOU between `stat` and `open` is not exploitable in the documented synthetic-only deployment but is a future hardening consideration.

Evidence: maintainer-reported `17/17` focused tests and `333/333` full tests at commit `c3762db30030814e8499d1ffef3ebeab88217421` in Python 3.14.10/Linux ARM64. No CI attestation, independent human review or production-credential validation.

## Security hardening in progress (issue #58)

The follow-up branch adds a **fail-closed Linux process gate**:
`PR_SET_DUMPABLE=0` is applied before the terminal asks for a passphrase.
Direct adapter access also checks `PR_GET_DUMPABLE == 0`. The selected
reader now reads from one `O_NOFOLLOW` file descriptor and checks the
unauthenticated KDBX header **before** deriving a key.

**Proposed KDF policy for this Ada-only vault:** KDBX4 with Argon2d or
Argon2id, 64–256 MiB memory, 3–10 iterations, 1–8 parallel lanes.
Reject legacy AES-KDF, weak KDF settings, and excessive resource requests
rather than silently opening them. A legitimate vault outside this range
must be reconfigured in KeePassXC; never bypass the policy via a flag.

The adapter calls `zeroize_credentials()` **immediately** after decrypting,
releasing the reader's stored password/key references. This remains *reference
release*, **not reliable Python memory zeroization**; decrypted entry strings
still live for the unlocked session. The test suite includes Linux subprocess
checks for process non-dumpability and sibling access denial, pending exact-head
validation on the target Mac.

**Dependency capture (not a completed lock):** `scripts/capture_kdbx_wheel_hashes.py`
uses only the Python standard library and pip's `--dry-run --report` support.
It must be executed **from the repo root** on the target **CPython 3.14 /
Linux aarch64** container. It requests binary-only wheels from PyPI,
requires precisely the seven package versions recorded during the synthetic
Docker test, extracts each actual wheel SHA-256 from pip's installation report,
and creates `requirements/kdbx-py314-linux-aarch64.txt`. It then checks
`pip install --dry-run --require-hashes` against that candidate lock.
The generated file requires **manual artifact and dependency review** before
committing/using it. It does not pin the remaining Python application
dependency graph, so this is **not yet a complete production build lock**.
There is no claim that a hash makes the upstream wheel trustworthy.

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
- `Kdbx4Reader.decrypt` uses unbounded `gzip.decompress` on the authenticated
  payload. The **encrypted file** is limited to 16 MiB by Ada, but the
  *decompressed* XML size is not explicitly bounded. This is a **potential
  resource-exhaustion risk** for unexpectedly large or deliberately crafted
  password-authorized KDBX content. Evaluate/reproduce before calling it a
  verified vulnerability. No user-controlled KDBX upload or web endpoint is
  exposed in Ada's current scope.

A targeted independent reader review remains mandatory before using any real
credentials, including payload-size behavior and verification that no
authenticated content is parsed before cryptographic checks.

## Decision

The project accepts **KDBX vault format + manual unlock** (ADR-0013).
It does **not** yet accept `kdbxtool` as production runtime library.
Prefer re-evaluating KeePassXC CLI over custom crypto if maturity/interop
checks on kdbxtool fail.
