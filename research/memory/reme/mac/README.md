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
- Workspaces and the virtual environment live under `/tmp` by default, outside the repository.
- The script never installs ReMe into Ada's `.venv` or modifies `pyproject.toml`.
- It never downloads an Ollama model. The already accepted local model must be present.
- ReMe Studio and MCP serving are disabled for the spike.
- Cloud-provider credentials are removed before runtime.
- The runtime points ReMe's OpenAI-compatible model wrapper to `http://127.0.0.1:11434/v1`.
- A proxy-based deny guard is applied to ordinary non-loopback HTTP traffic after package installation.

The proxy guard is **not a kernel-level proof of zero egress**. The result bundle also captures established ReMe TCP connections when `lsof` is available. A later hard-egress test can use a dedicated network sandbox if this becomes decision-changing.

## Pinned research baseline

The default executable baseline is:

```text
Python          3.14.x (exact major/minor required)
ReMe            0.4.1.12
AgentScope      resolved from ReMe's pinned `as` extra
Model           qwen3.5:9b
Ollama endpoint http://127.0.0.1:11434/v1
```

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

Useful explicit overrides:

```bash
PYTHON_BIN=python3.14 \
OLLAMA_MODEL=qwen3.5:9b \
ADA_REME_SPIKE_ROOT=/tmp/ada-reme-explicit \
sh research/memory/reme/mac/run.sh
```

Do not use `REME_VERSION` to silently move to a newer release. A version change is a separate characterization input and should be recorded as such.

## Output

The final console output prints the result directory, for example:

```text
/tmp/ada-reme-spike-20260921-161500
```

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

Do not commit the result directory.

## Retry only the local LLM step

If the main run already passed installation/file/isolation tests and only `local-llm-memory-flow` failed, reuse the existing virtual environment and workspace instead of reinstalling ReMe:

```bash
sh research/memory/reme/mac/resume-llm.sh /path/to/ada-reme-spike-RESULT
```

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

Two prepared ADR tests remain outside this first executable harness:

- **External document adapter**: Ada has not yet accepted the provider-independent source-reference contract, so the harness must not invent production adapter code merely for the spike.
- **ReMe vs Hindsight quality benchmark**: run this only after ReMe's native retrieval weaknesses are measured. Hindsight should not be introduced just to create a benchmark dependency.

See `../spike-plan.md` and `../scenario-matrix.md` for the full decision context.
