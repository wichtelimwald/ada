# ADR-0010: File-native Memory write safety and Git history adapter

- **Status:** Proposed
- **Date:** 2026-09-26

## Context

ADR-0008 accepts human-editable current Markdown as authoritative Memory and allows
Git-style per-domain history for recovery/versioning, provided history is never
treated as current Memory. MVP-20 must make that design safe enough to build
protection domains on top of it.

The MVP-10 adapter still has four implementation gaps relevant here:

1. generic callers supply semantic entry slugs;
2. corrections have no explicit optimistic-revision contract;
3. file reads/writes and bootstrap publication are not yet hardened for the target
   local POSIX profile;
4. runtime writes do not capture human edits or Ada writes in history.

## Decision

### 1. Current files remain authoritative

`memory/` and `learning/` current files are the only semantic source read by
normal Memory APIs. Git objects, commits, snapshots and backups are recovery/history
only and must never be consulted to reconstruct current Memory automatically.

### 2. Generic IDs are random and opaque

Ada generates generic entry IDs from UUIDv4 randomness. IDs contain no timestamp,
meaningful slug, person name or Memory content. The logical ID remains stable across
explicit correction/promotion. Public create APIs do not accept caller-selected
generic IDs.

A forgotten ID remains reserved by its tombstone/history and is never reused.

### 3. Create and correction are different operations

Creation fails closed on any collision.

Correction requires an existing established entry plus the revision observed by the
caller. If current content no longer matches that revision, Ada returns a conflict
and preserves the current file. Explicit correction keeps the same logical ID,
changes the authoritative content, and records the prior version only in history.

This is not last-write-wins conflict resolution.

### 4. Ada writers serialize locally; human edits remain out-of-band authority

Ada-originated writes are serialized with an OS file lock for the Memory root.
Before an Ada write, the history adapter captures already-present out-of-band
changes under `memory/` and `learning/`. The write then rechecks its expected
revision and fails on staleness. A successful Ada write is captured immediately.

Ordinary human editors are not required to use Ada's lock. The optimistic revision
is therefore the semantic conflict boundary: a human edit observed before the Ada
publication wins and requires reconciliation rather than overwrite.

### 5. Use an external Git CLI behind an Ada-owned adapter

Ada uses the installed Git CLI for this MVP history adapter instead of adding
GitPython, Dulwich or pygit2.

Reasons:

- Git already implements the required durable history semantics.
- Git's pathspec-aware commit supports committing the intended path(s) while
  disregarding unrelated staged contents.
- It adds no Python dependency or native Python extension.
- The adapter can be replaced later without changing Memory semantics.

The adapter disables global/system Git configuration and user-level Git
ignore/attributes files, pins every command to the Memory root's own `.git` so a
missing history never falls back to an enclosing repository, uses literal
pathspecs, a fixed non-authenticating Ada history identity, and no remote/network
commands. It records only non-hidden Markdown files so OS/editor artifacts such
as AppleDouble `._*.md` files stay out of history. An existing Git `index.lock`
stops the operation before an Ada write is published; other Git/lock failures
after publication are reported as an explicit ambiguous outcome. Ada never
deletes an unexplained Git lock.

Git is GPLv2 and is treated as a separately installed external executable, not
vendored or redistributed by Ada in this decision. Future packaging/distribution
must explicitly decide how Git is provisioned and review the resulting artifact.

Evidence used for this implementation choice:

- Git commit/pathspec behavior: https://git-scm.com/docs/git-commit
- Git licensing/project information: https://git-scm.com/about/free-and-open-source
- GitPython package metadata: https://pypi.org/project/GitPython/
- Dulwich package metadata: https://pypi.org/project/dulwich/
- pygit2 package metadata: https://pypi.org/project/pygit2/

Alternatives considered:

- **GitPython 3.1.x (BSD-3-Clause):** maintained and convenient but still shells
  through/depends on Git while adding another Python dependency.
- **Dulwich 1.2.x (Apache-2.0 OR GPL-2.0-or-later):** pure-Python Git implementation
  can remove the executable dependency, but adds substantial runtime surface not
  needed for this slice.
- **pygit2 1.20.x (GPLv2 with linking exception):** mature bindings, but native
  libgit2 artifacts expand platform/distribution review.

### 6. Harden the supported local storage profile

For MVP-20 the supported profile is local POSIX storage on the project's macOS/Linux
targets.

- Reads use fd-based no-follow opens and verify regular files.
- Writes use durable temporary files, file fsync, atomic replace where replacement
  is intended, and directory fsync before success.
- Create-only publication prefers hard-linking a fully synced temp file and falls
  back to `O_CREAT|O_EXCL` direct creation when hard links are unavailable.
  A crash during the fallback may leave a visibly malformed/incomplete file; this
  is an integrity error and must never be treated as absent or silently overwritten.
- Personality bootstrap uses create-only publication. If another writer wins, the
  winner is re-read and used.
- Malformed established Memory is an integrity error. Ordinary forget does not
  erase/replace it; repair is required before forgetting until a separately
  authorized recovery path exists.

Network/distributed filesystem semantics and Windows are not accepted by this ADR.

## Consequences

### Positive

- Current Memory remains human-readable and independent of Git internals.
- Human edits present at Ada's final revision check cannot be silently replaced
  by a stale Ada correction.
- Recovery history is inspectable with standard Git tooling.
- No new Python dependency is required.
- The implementation remains replaceable before consumer packaging.

### Costs / limitations

- Git must be installed for this development Memory profile.
- Git history retains forgotten/superseded content until a separate purge policy is
  executed.
- Protection domains/encryption are still absent; this remains unsuitable for real
  household Memory until MVP-30.
- Non-cooperating editors can still modify files between operations. Ada rechecks the
  expected content revision immediately before replace/delete and verifies the result,
  but POSIX path replacement is not a true cross-application compare-and-swap. The
  adapter therefore detects practical stale-write windows and fails closed where it
  can, without claiming an impossible mandatory lock for ordinary editors.
  Concretely, a human save (in-place or rename) that lands after the final revision
  check but before Ada's replace/delete is overwritten without a history entry and
  Ada still reports success; later edits are detected and reported as conflicts.
- Repo-local Git configuration and attributes under `<root>/.git` are trusted. Any
  principal that can write there can make Git execute commands as Ada (for example
  via `core.fsmonitor`). MVP-20 assumes only the owning OS user can write the Memory
  root; protection domains must not leave history metadata writable by untrusted
  vault editors or sync tools.
- Packaging must revisit the external Git prerequisite.

## Re-open triggers

Reconsider this adapter if:

- Git provisioning becomes unacceptable for the supported end-user package;
- target storage cannot provide the required local POSIX durability semantics;
- encrypted protection domains require a history backend that Git cannot support
  safely/operationally;
- deterministic tests expose an uncloseable lost-update/crash-recovery failure.
