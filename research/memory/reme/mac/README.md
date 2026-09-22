# ReMe macOS characterization harness

This directory prepares the executable part of ADR-0008's ReMe evaluation.

It is **research infrastructure only**. It does not add ReMe to Ada's production dependencies and does not accept ADR-0008.

## What the harness proves

The automated run covers the decision-changing cases that can be tested safely with synthetic data:

1. **Target platform** — macOS Apple Silicon and exactly Python 3.14; no silent Python downgrade.
2. **Minimal package path** — installs pinned `reme-ai[as]`, not `reme-ai[core]`.
3. **Real import/start path** — catches hidden dependencies on optional AgentScope/Claude/Codex components.
4. **Local model path** — ReMe uses Ada's already accepted loopback OpenAI-compatible Ollama endpoint.
5. **File/source truth** — write/search round trip through the real ReMe HTTP Job API.
6. **Ada metadata coexistence** — nested `ada.state`, `ada.confirmation_basis`, and `ada.subject` frontmatter must survive ReMe file operations.
7. **Out-of-band edit + clean rebuild** — edit Markdown while stopped, discard `metadata/`, restart, and verify search follows current files.
8. **Operational forget** — delete current Memory, discard derived metadata, rebuild, and verify the forgotten canary does not return.
9. **Protection-domain isolation** — run two ReMe workspaces concurrently with mutually exclusive synthetic canaries.
10. **Resource footprint** — capture ReMe's `status` for one and two concurrent workspaces.
11. **Learning observation** — run Auto Memory and Auto Dream for a preference, an explicit correction, and an unresolved contradiction; preserve the generated artifacts for review.
12. **Dependency evidence** — capture `pip freeze`, `pip inspect`, and package license metadata from the exact environment.

The learning cases deliberately do **not** reduce semantic correctness to brittle string assertions. Their generated `daily/`, `digest/`, and `session/` artifacts are the evidence to inspect against Ada's lifecycle rules.

## Safety properties

- Fixtures are synthetic canaries only. Do not replace them with personal data.
- Workspaces and the virtual environment live under the repository's Git-ignored `.artifacts/research/memory/reme/` tree by default.
- The script never installs ReMe into Ada's `.venv` or modifies `pyproject.toml`.
- It never downloads an Ollama model. The already accepted local model must be present.
- ReMe Studio and MCP serving are disabled for the spike.
- Cloud-provider credentials are removed before runtime.
- Runtime model access stays local to the host Ollama service.
- A proxy-based deny guard is applied to ordinary non-loopback HTTP traffic after package installation.

The proxy guard is **not a kernel-level proof of zero egress**. The result bundle also captures established ReMe TCP connections when `lsof` is available.

This ReMe lane intentionally runs on the macOS host because one of its decision gates is the real target-Mac/Python-3.14 runtime. That is an explicit exception to the containerized comparison lanes, not the default pattern for new third-party research. LangMem, Hindsight, and Letta comparisons run in ephemeral sandbox containers.

## Pinned research baseline

The default executable baseline is:

```text
Python          3.14.x (exact major/minor required)
ReMe            0.4.1.12
AgentScope      resolved from ReMe's pinned `as` extra
Model           qwen3.5:9b
Ollama endpoint http://127.0.0.1:11434/v1
```

The harness overlays `spike-config.yaml` on ReMe's published defaults:

```text
LLM max tokens       4096
LLM context size     32768
ReAct max iterations 8
Auto Memory          no derived auto-tag step
Auto Dream           no derived auto-tag step
Dream units          max 5
```

These are characterization bounds, not Ada production defaults. They isolate ReMe's core Memory behavior from optional derived tagging and from ReMe's much larger general-purpose output/ReAct limits.

The current characterization uses AgentScope's **native Ollama backend**, not Ollama's OpenAI-compatible `/v1` endpoint. This is deliberate: the native backend passes `think=false` explicitly for `qwen3.5:9b`, maps output limits to Ollama's `num_predict`, and forwards tool schemas through Ollama's native chat API.

Before starting ReMe, the harness now performs a direct native Ollama tool-call probe. This separates a model/tool-calling problem from a ReMe Memory-agent problem.

`REME_VERSION` and `OLLAMA_MODEL` are overridable for explicit comparison runs, but the first result should use the defaults.

## Run

From the Ada repository root:

```bash
sh research/memory/reme/mac/run.sh
```

The script checks prerequisites before changing anything. It requires:

- macOS on Apple Silicon;
- `python3.14`;
- `curl`;
- Ollama running locally;
- `qwen3.5:9b` already installed;
- network access during the isolated PyPI install step.

Useful explicit overrides remain available for deliberate comparisons, but ordinary runs should keep the default repo-local artifact path:

```bash
PYTHON_BIN=python3.14 OLLAMA_MODEL=qwen3.5:9b sh research/memory/reme/mac/run.sh
```

Do not use `REME_VERSION` to silently move to a newer release. A version change is a separate characterization input and should be recorded as such.

## Output

The final console output prints the repo-local result directory, for example:

```text
.artifacts/research/memory/reme/run-20260922-063000
```

`.artifacts/research/memory/reme/latest` points to the newest default run.

Primary artifacts:

```text
SUMMARY.md
summary.json
environment.txt
pip-freeze.txt
pip-inspect.json
package-metadata.json
network-connections.txt
logs/
basic/
isolation/
llm-flow/
workspace-a/
workspace-b/
```

`summary.json` is intentionally compact. A `FAIL` is a **research finding**, not automatically a ReMe rejection. Always inspect the corresponding log and captured source artifacts.

The complete `.artifacts/` tree is ignored by Git.

## Retry only the local LLM step

If the latest main run passed installation/file/isolation tests and only `local-llm-memory-flow` failed, reuse its existing virtual environment with:

```bash
sh research/memory/reme/mac/resume-llm.sh
```

An explicit result directory can still be passed for an older run.

The retry reuses the existing virtual environment but creates a **fresh ReMe workspace and output directory** for each attempt. This avoids contamination from a request that timed out after writing a partial session. It also prints the relevant driver/service log tails on failure.

LLM-driven HTTP calls use longer research timeouts than ordinary file/search operations:

- Auto Memory: 300 seconds;
- Auto Dream: 600 seconds.

These are harness timeouts, not Ada production defaults.

## Interpreting important failures

### `install-reme` fails on Python 3.14

Record this as a target-platform incompatibility. Do not change Ada's Python baseline automatically. A later comparison run on an upstream-supported Python version may identify whether the problem is packaging-only.

### Service does not start with `reme-ai[as]`

This is important evidence that ReMe's practical minimum dependency path is larger than its package extras suggest. Do not make the harness install `core` automatically.

### Ada frontmatter disappears or is rewritten

This is a major adapter-feasibility concern. ReMe must be able to coexist with Ada-owned lifecycle/trust metadata without becoming its authority.

### Old canary returns after clean rebuild

This fails the authoritative-file / operational-forget gate and is potentially disqualifying until explained.

### Private-B canary appears in workspace A

Stop evaluation and treat it as a protection-domain isolation failure.

### Auto Memory/Dream differs from Ada semantics

Expected possibility. Inspect the generated artifacts and decide what the Ada adapter must override. ReMe is not allowed to define Ada's permission or trust lifecycle.

## Deliberately not automated yet

One prepared ADR test remains outside this first executable harness:

- **External document adapter**: Ada has not yet accepted the provider-independent source-reference contract, so the harness must not invent production adapter code merely for the spike.

The broader ReMe/LangMem/Hindsight/Letta comparison now lives under `research/memory/comparison/`.

See `../spike-plan.md` and `../scenario-matrix.md` for the full decision context.
