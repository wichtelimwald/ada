# Ada Memory four-candidate comparison

This harness compares **ReMe, LangMem, Hindsight, and Letta MemFS side by side** without selecting a winner.

## One command

From the Ada repository root:

```bash
sh research/memory/comparison/run-all.sh
```

All virtual environments, npm packages, local databases, logs, and generated memory artifacts are written under a temporary result directory outside the repository. The final console output prints that directory and its `SUMMARY.md`.

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

## Prerequisites

- macOS Apple Silicon target used by Ada;
- `python3.14`;
- local Ollama with `qwen3.5:9b`;
- internet access for isolated package installs;
- Node/npm >= 22.19 for the Letta lane. If Node is missing/too old, Letta is reported `BLOCKED` and the other lanes still run.

The Hindsight lane may download its local ONNX embedding model on the first run.

## Output

Typical result layout:

```text
/tmp/ada-memory-compare-<timestamp>/
├── SUMMARY.md
├── comparison.json
├── logs/
├── reme/
├── langmem/
├── hindsight/
└── letta/
```

Do not commit result bundles. They are synthetic research artifacts.
