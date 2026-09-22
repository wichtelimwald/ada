# Ada Memory four-candidate comparison

This harness compares **ReMe, LangMem, Hindsight, and Letta MemFS side by side** without selecting a winner.

## One command

From the Ada repository root:

```bash
sh research/memory/comparison/run-all.sh
```

All virtual environments, npm packages, local databases, logs, and generated memory artifacts stay inside the checked-out repository under the Git-ignored `artifacts/` tree.

The default result path is:

```text
artifacts/research/memory/comparison/run-<timestamp>/
```

`artifacts/research/memory/comparison/latest` points to the most recent run.

## Fair-comparison rule

The comparison has two tracks:

1. **Semantic track** — every candidate receives the same synthetic preference, explicit correction, and unresolved-conflict fixtures.
2. **Substrate track** — human-readable authority, rebuild/edit, forgetting, and isolation are exercised only where the candidate actually owns those concerns. Missing/non-applicable capabilities are recorded as `N/A`, `NOT CHARACTERIZED`, or `GAP`, not manufactured failures.

A runtime `PASS` means only that the prepared lane completed. It is **not** a semantic score or architecture decision.

## Common semantic fixtures

- explicit communication preference with evidence token;
- initial music lesson `Wednesday 17:00`;
- explicit correction to `Thursday 17:00`;
- independent pickup claim `16:00`;
- conflicting pickup claim `17:00` explicitly marked as **not** a correction;
- synthetic canaries for forget and isolation where applicable.

## Candidate lanes

### ReMe 0.4.1.12

Reuses the existing full macOS characterization harness: Markdown/YAML, rebuild, forget, workspace isolation, native Ollama, Auto Memory, and Auto Dream.

### LangMem 0.0.30

Tests storage-agnostic structured memory extraction/update against local `qwen3.5:9b` via `langchain-ollama`. This lane asks whether LangMem can supply the correction/contradiction semantics ReMe lacks without introducing another authoritative store.

### Hindsight 0.10.1

Runs an isolated embedded database with local Ollama and local ONNX embeddings. Tests retain/recall/reflect, observation consolidation, bank isolation, provenance/source facts, and document forgetting.

### Letta Code / MemFS 0.32.15

Installs Letta Code into an isolated npm prefix and uses its experimental local backend with Ollama. The first lane focuses on whether the Git-backed Markdown MemFS represents the common preference/correction/conflict fixtures coherently. Forget/isolation remain follow-ups rather than being faked in the initial run.

## Execution boundary

The comparison deliberately does **not** install every candidate into the maintainer's host or persistent Dev Container.

- **ReMe** remains a host-side exception because its existing lane explicitly characterizes the real macOS/Apple-Silicon/Python-3.14 target.
- **LangMem, Hindsight, and Letta** run in short-lived Docker containers.
- those containers use a read-only root filesystem;
- Linux capabilities are dropped;
- `no-new-privileges` is enabled;
- PID count is bounded;
- the Ada repository is mounted read-only;
- only that candidate's `artifacts/...` result directory is writable;
- candidate containers are removed after the lane finishes.

This keeps the persistent Dev Container clean while applying the same container/sandbox principle to unselected third-party candidates.

This is development isolation, not Ada's production authorization model. Network access remains available because candidate installation and Hindsight's first local embedding-model setup may require downloads.

## Prerequisites

- macOS Apple Silicon target used by Ada;
- `python3.14` and local Ollama with `qwen3.5:9b` for the ReMe target-Mac lane;
- Docker available/running for LangMem, Hindsight, and Letta sandbox lanes;
- internet access for isolated package/container/model downloads.

Host Node/npm is no longer required; the Letta lane uses a pinned Node 22 container.

The Hindsight lane may download its local ONNX embedding model on the first run.

## Output

Typical result layout:

```text
artifacts/research/memory/comparison/
├── latest -> run-<timestamp>
└── run-<timestamp>/
    ├── SUMMARY.md
    ├── comparison.json
    ├── logs/
    ├── reme/
    ├── langmem/
    ├── hindsight/
    └── letta/
```

The complete `artifacts/` tree is ignored by Git.

## Legacy artifact migration

Older harness versions wrote result bundles to macOS temporary directories. Preserve those results and bring them into the repository workspace with:

```bash
sh research/memory/migrate-legacy-artifacts.sh
```

They are moved under:

```text
artifacts/research/memory/legacy/
```

Moved virtual environments are evidence only and should not be resumed after relocation.

## Cleanup

Remove all repo-local Memory research artifacts:

```bash
sh research/memory/clean-local.sh
```

If the old temporary artifacts are no longer needed and were not migrated, they can be removed explicitly with:

```bash
sh research/memory/clean-local.sh --legacy
```

Both cleanup commands are intentionally scoped to Ada Memory research artifacts.
