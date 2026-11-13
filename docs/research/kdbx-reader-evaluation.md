# KDBX reader for Ada — experimental compatibility gate

**Date:** 2026-11-13  
**Status:** PoC only — no real credentials, no production library approval.

## Requirement and threat boundary

One encrypted Ada-only KDBX file under the configured persistent Memory
storage root (`secrets/ada.kdbx`), read by the container after a human
passphrase prompt. No Keychain/1Password access, no automatic unlock, no
password in argv/env/logs, no model-facing secret tool. The vault is not
semantic Memory and is excluded from Git history and retrieval.

The PoC only verifies a one-shot **unlock then lock** command. It does not
unlock the already-running application or provide live IONOS integration.

## Reader alternatives and license gate

| Option | Evidence | Assessment |
| --- | --- | --- |
| PyKeePass 4.2.0 | Python KDBX3/4 reader; GPL-3.0 ([PyPI](https://pypi.org/project/pykeepass/)) | Mature relative to new alternatives; adding this Python runtime library risks copyleft obligations when distributing Ada under MIT. Not selected. |
| KeePassXC CLI | Native CLI, GPLv3; KDBX support ([official documentation](https://keepassxc.org/docs/KeePassXC_UserGuide)) | Independent binary/process possible, but additional Linux/Qt packages and IPC/per-call passphrase handling. Reserve fallback if the Python option fails. Requires separate artifact-level distribution review. |
| kdbxtool 0.1.7 | Python >=3.12, Apache-2.0, KDBX4/Argon2; [PyPI](https://pypi.org/project/kdbxtool/), [source](https://github.com/coreyleavitt/kdbxtool) | **Opt-in PoC reader only.** No GPL linking. Alpha, single maintainer, minimal adoption, Python 3.14 and KeePassXC-produced KDBX compatibility unverified. |
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

- `docker build --target secrets-poc`: optional reader installs and runs on
  Ada's Python 3.14 Linux target (not verified).
- `ada secrets-check --memory-root ...` on an interactive Docker terminal:
  opens a genuine KeePassXC-created KDBX4/Argon2 file; input is hidden and
  nothing secret is printed; wrong password fails closed (not verified).
- Non-interactive invocation refuses to prompt; restart prompts again
  rather than retaining a decryption token.
- A secret reference not in the trusted allowlist is denied by the adapter;
  missing/duplicate entries fail closed. Unit tests use synthetic fake DB.
- Git Memory history never stages `secrets/`; regular manual `git add -A`
  excludes it; forced addition is detected and refused on next Memory init.
  **Manual `git add -f` can still force a secret into history and cannot be
  undone by ignore rules.** Operators must review backups/sync and history.
- Reading a real secret never enters model context or DBOS. Live calendar
  wiring, complete entry access/authorization and in-process startup unlock
  are **not implemented** in this PoC.

## Decision

The project accepts **KDBX vault format + manual unlock** (ADR-0013).
It does **not** yet accept `kdbxtool` as production runtime library.
Prefer re-evaluating KeePassXC CLI over custom crypto if maturity/interop
checks on kdbxtool fail.
