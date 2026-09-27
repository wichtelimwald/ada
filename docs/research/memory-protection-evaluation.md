# MVP-30 Memory protection mechanism evaluation

Status: decision evidence for proposed ADR-0011  
Date: 2026-09-28

## Question

Which maintained mechanism should Ada adapt for encrypted, human-editable Memory
protection domains on the first supported macOS MVP, while keeping the broker and
domain semantics Ada-owned and avoiding unnecessary runtime dependencies?

This evaluates the protection/storage mechanism only. It does not delegate
authorization, Memory semantics, retrieval, or action authority to a third party.

## Requirements

A serious candidate must support or preserve:

- encryption at rest for each protection domain;
- ordinary human editing of Markdown while a domain is unlocked;
- no plaintext credential in repository/config/logs;
- no cloud service requirement;
- an Ada-owned request-scoped broker boundary;
- encrypted history as well as current Memory;
- restart/restore testing;
- a credible maintenance and license story;
- the current macOS MVP without unnecessarily closing a later Linux/server path.

## Candidates

| Candidate | License / platform | Evidence | Fit |
| --- | --- | --- | --- |
| macOS encrypted disk image behind an Ada adapter | Platform capability; no new redistributed dependency. Apple documents encrypted writable disk images and growable image formats; the current hdiutil man page documents AES-128/AES-256, stdin password input and SPARSEBUNDLE, while macOS 27 deprecates hdiutil in favor of diskutil image. Ada must therefore depend on a platform-vault adapter, not a command name. | https://support.apple.com/guide/disk-utility/dskutl11888/mac and https://keith.github.io/xcode-man-pages/hdiutil.1.html | **Best MVP control.** Native mounted filesystem keeps Markdown directly editable and avoids FUSE/Java/Python crypto dependencies. macOS-specific implementation must remain replaceable. |
| gocryptfs | MIT; current project status is mature on Linux, while macOS is explicitly described as beta quality and requires FUSE. The repository currently lists v2.6.1 as the latest changelog release. | https://github.com/rfjakob/gocryptfs | Strong Linux candidate later, but adds FUSE and a weaker macOS support posture than the platform capability. |
| CryFS | LGPL-3.0. The project still points to a stable 1.0 branch, but current 2.0 development is alpha/experimental, warns of data loss, and lists macOS as untested. | https://github.com/cryfs/cryfs | Do not choose for the macOS MVP: using the legacy stable line or the untested alpha line both create avoidable platform/maintenance risk. |
| Cryptomator Desktop | GPL-3.0 or commercial licensing for some integrations; mature end-user encrypted vault product, Java-based application. | https://github.com/cryptomator/cryptomator | Good user product, but too large a runtime/application dependency for Ada's narrow host-side broker primitive. |
| Cryptomator CLI / cryptofs | AGPL-3.0 or commercial dual licensing; Java filesystem provider. | https://github.com/cryptomator/cli and https://github.com/cryptomator/cryptofs | Technically relevant, but adds Java/runtime and stronger distribution obligations without solving Ada's authorization/broker semantics. |
| age | BSD-style 3-clause license; maintained simple file-encryption tool/library ecosystem. v1.3.2 was released on 2026-08-29 with Darwin arm64 binaries. | https://github.com/FiloSottile/age and https://github.com/FiloSottile/age/releases | Excellent candidate for exports/backups or envelope files, but it is file encryption rather than a directly editable mounted vault. Using it for every Markdown edit would require Ada to invent a plaintext-workspace lifecycle. |
| Whole-disk FileVault only | macOS platform feature. | https://support.apple.com/guide/mac-help/protect-data-on-your-mac-with-filevault-mh11785/mac | Useful defense for the device but not a separate per-person/shared protection-domain boundary once the logged-in account can read everything. |

## Key storage

Apple Keychain is the first-platform control for small secrets. Apple's Keychain
Services documentation positions the keychain as encrypted storage for passwords,
keys and other small secrets, with access controls on macOS:

- https://developer.apple.com/documentation/security/keychain-services
- https://developer.apple.com/documentation/security/adding-a-password-to-the-keychain

For the command-line prototype, the macOS security tool supports generic password
items and application access restrictions. Broad allow-any-application access is
explicitly documented as insecure and must not be used:

- https://keith.github.io/xcode-man-pages/security.1.html

The exact Keychain access-control shape must be validated on the target Mac before
ADR-0011 can become Accepted. Secrets must be piped through standard input/API
memory, never placed in command arguments, environment variables, config files, or
logs.

## Git history implication

ADR-0010 currently stores .git below the human-editable Memory root. That is not
sufficient for MVP-30: repository-local Git config/attributes can affect command
execution, and Git objects contain historical plaintext.

The protected design therefore needs two independently controlled surfaces per
domain:

1. a human-editable encrypted current-Memory surface; and
2. broker-controlled encrypted history metadata/object storage that ordinary
   editors and sync tools cannot modify.

The implementation can still use Git behind the existing Ada adapter, but its
GIT_DIR must become separately configurable and protected while the current
working tree remains human-readable when unlocked.

## Multi-workspace concurrency evaluation

Separate human/editor and Ada Git workspaces would remove ADR-0010's final
same-working-tree publication race only if ordinary human edits participate in a
commit/synchronization protocol. Normal editors do not provide that contract by
themselves. Adding a watcher, auto-committer and merge/publish engine now would be a
second synchronization system, not a small protection-domain change.

Proposed MVP direction:

- retain MVP-20's optimistic revision checks for current Markdown in the first
  protection-domain implementation;
- keep the known late non-cooperating-save race explicit;
- do not claim Git worktrees/clones solve it until a concrete human-edit workflow
  is designed and tested;
- treat acceptance of that residual versus a stronger synchronization slice as an
  explicit ADR-0011 review decision before MVP-30 is marked done.

## Recommendation

For the first macOS MVP, adapt the platform encrypted-volume capability behind an
Ada-owned EncryptedVaultProvider boundary and use Keychain for per-domain secret
material. Do not make hdiutil itself architectural: use the currently supported
platform command only inside the adapter and retain a migration path to diskutil
image.

Do not add gocryptfs, CryFS, Cryptomator, age, or a Python crypto package to the
runtime for the live-vault problem at this stage. Re-evaluate gocryptfs or another
maintained provider when Linux/server deployment becomes an implemented
requirement. Re-evaluate age separately for backup/export if its simpler
file-encryption model fits that later slice.
