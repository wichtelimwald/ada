# Results — Ollama API-path isolation experiment

**Status:** Executed successfully on target MacBook Air M1 / 16 GB.

## Environment

- Ollama: 0.33.2
- model: `ada-qwen3-8b-4k` (base `qwen3:8b`)
- context: 4096
- Python: 3.14.6
- macOS / Apple M1 / 16 GB

## Native `/api/chat`

- warm-up: 11.180 s
- measured: 10.863 / 10.614 / 10.673 s
- mean: **10.717 s**
- median: **10.673 s**
- all valid: yes

## OpenAI-compatible `/v1/chat/completions`

- warm-up: 10.762 s
- measured: 10.572 / 11.066 / 10.938 s
- mean: **10.859 s**
- median: **10.938 s**
- all valid: yes

## Conclusion

The Ollama protocol path is **not** the cause of the previously observed PydanticAI latency.

The two direct API paths differ by only ~0.14 s in mean runtime (~1.3%). Both execute the same two-call tool workflow correctly in about 10.7–10.9 seconds.

Therefore:

- do not attribute the PydanticAI 45–106 s measurements to Ollama's OpenAI-compatible endpoint;
- the remaining difference lies in PydanticAI request/profile/runtime behavior or configuration;
- OpenJarvis' ~8.6 s result is broadly consistent with direct Ollama performance.

A follow-up source inspection identified a likely configuration/profile cause: unified `thinking=False` is profile-dependent in PydanticAI, while an explicit provider setting `openai_reasoning_effort="none"` is sent directly. The final Pydantic rerun should use that explicit setting.
