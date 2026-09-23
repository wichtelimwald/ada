# Privacy principles

> This document defines design commitments for Ada. A narrow local-chat and synthetic calendar-action slice exists; the full privacy and Memory behavior described here is not yet implemented.

## Commitments

1. **Local-first by default.** Prefer local processing and local storage where practical. Local processing is not automatically private: logs, caches, swap, backups, sync, update checks, model downloads, and crash data can still expose information.
2. **No hidden cloud egress.** Any remote model or service integration must document what data leaves the device and why.
3. **Data minimization.** Send or retain only the context required for the requested task.
4. **No telemetry by default.** Telemetry must be opt-in, documented, and separable from core functionality.
5. **User-controlled memory.** Stored personal memory must be inspectable, editable, exportable, and deletable.
6. **Deletion must cover derived local data.** Deleting source memory should also remove or invalidate associated indexes, embeddings, caches, transcripts, summaries, and logs where technically applicable. Data already transmitted to third parties is subject to that provider's retention/deletion capabilities and must not be presented as locally reversible.
   Removal from current retrieval does not purge version-control history, backups, or shared copies. Permanent erasure and narrowing a previously shared note require a separate, verified purge policy; changing its current folder alone does not revoke access to its earlier shared history.
7. **Separate secrets from memory.** Credentials and secrets must not live in prompts, normal memory, logs, repository files, or general-purpose note stores.
8. **Sensitive data needs explicit boundaries.** Microphone, camera, screen content, personal documents, contacts, browser data, and private memory require explicit data-flow documentation.
9. **Backup and sync are data egress.** A local file that is synchronized through iCloud, Dropbox, OneDrive, Git, backup software, or another service is not local-only. Sync/backup behavior must be explicit.
10. **Cloud fallback must be transparent.** If a task would materially benefit from remote processing, the UI should make the provider and data scope understandable before sensitive data is sent.
11. **Plugins and extensions are a trust boundary.** Third-party plugins, skills, MCP servers, models, and binaries must not be installed or executed solely because an agent requested them.

## Required documentation before implementation

Any component that reads, derives, stores, backs up, synchronizes, or transmits personal data must document:

- source data and derived data,
- data stored,
- data transmitted,
- retention and deletion behavior,
- backup/sync behavior,
- encryption/protection,
- user controls,
- failure modes,
- third parties involved.

See `docs/privacy/` and `docs/security/threat-model.md`.
