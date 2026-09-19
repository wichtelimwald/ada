# Ollama API-path isolation experiment

**Status:** disposable architecture experiment, not Ada production code.

## Question

The local framework benchmark showed a large latency gap:

- OpenJarvis uses Ollama's native `/api/chat`
- PydanticAI uses Ollama's OpenAI-compatible `/v1/chat/completions`

Before attributing the gap to either framework, this probe removes both frameworks and compares those two Ollama API paths directly.

## Controlled variables

Both paths use:

- model: `ada-qwen3-8b-4k`
- base model: `qwen3:8b`
- context: 4096 via the model alias
- temperature: 0
- max output tokens: 256
- same prompt
- same single `calendar_conflicts` tool
- one tool call followed by one final response
- thinking/reasoning disabled
- one warm-up per path
- three interleaved measured runs

## Run

```bash
uv run python ollama_api_benchmark.py
```

No Python package dependencies are required.

## Interpretation

- native fast + OpenAI-compatible slow → provider/API-path cost dominates; do not penalize PydanticAI core runtime
- both fast → investigate PydanticAI model/provider integration
- both slow → OpenJarvis native result was using another materially different configuration
