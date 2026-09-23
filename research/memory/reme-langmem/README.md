# ReMe + LangMem final architecture characterization

This research spike validates the **combined role split** selected by the frozen
ADR-0008 decision matrix. It is not production Memory code.

## Architecture under test

```text
user-owned Markdown/YAML
        ^
        | accepted canonical write
Ada deterministic validation
        ^
        | typed semantic proposal
     LangMem
        ^
        | minimal observation + existing record
        |
Ada application

ReMe observes the Markdown vault and provides read/search through
a restricted stdio-MCP subprocess.
```

The important boundaries are:

- **ReMe/Markdown is authoritative**; ReMe model-generated Auto Memory/Dream is
  not used for canonical writes in this spike.
- **LangMem only proposes semantic changes**. Its schema contains no provenance,
  scope, authority, or permission fields.
- **Ada supplies provenance externally** and validates correction/conflict
  behavior before any Markdown write.
- **AdaGuard remains authority**. Nothing in Memory or LangMem can grant rights.
- ReMe runs out-of-process over **stdio MCP**, not unauthenticated localhost
  HTTP. The tool allowlist is read-only: `version`, `status`, `search`,
  `read`.
- The test uses synthetic canaries only.

## What the run checks

1. Python 3.14 / Apple Silicon / local Ollama prerequisites.
2. One combined venv containing **Ada's actual current package** plus:
   - `pydantic-ai-slim[openai]==2.46.0`
   - `cedarpy==4.12.0`
   - `dbos==3.0.0`
   - `reme-ai[as]==0.4.1.12`
   - `langmem==0.0.30`
   - `langchain-ollama==1.1.0`
   This makes dependency compatibility with Ada's accepted runtime part of the gate, not a later assumption.
3. Security floors for vulnerable LangChain/LangGraph lines:
   - `langchain-core >= 1.3.3`
   - `langgraph >= 1.0.10,<2`
   - `langgraph-checkpoint >= 4.1.1`
4. `pip check`, exact freeze, `pip inspect`, package/license metadata, and
   installed footprint.
5. A separate `pip-audit` pass when available.
6. ReMe starts through stdio MCP and exposes only the read-only allowlist.
7. LangMem explicit correction proposal is accepted only after deterministic
   validation and Ada-supplied provenance.
8. A non-correction conflict must preserve the existing claim and add a second
   claim instead of overwriting it.
9. A synthetic silent-overwrite proposal is rejected by the validator.
10. ReMe finds accepted Markdown writes.
11. An out-of-band Markdown edit remains authoritative and is re-indexed by
    ReMe.

## Run

From the repository root on the target Mac:

```bash
sh research/memory/reme-langmem/run.sh
```

The script writes only git-ignored research output under:

```text
artifacts/research/memory/reme-langmem/
```

Upload/share only:

```text
artifacts/research/memory/reme-langmem/latest/REVIEW-BUNDLE.txt
```

A failure is a research finding, not automatically a framework rejection.
On failure, the bundle includes the last 100 lines of the integration log and
any semantic proposals recorded before validation. An incomplete integration
result is not a passing result.
