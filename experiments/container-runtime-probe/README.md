# Container runtime probe

**Status:** disposable architecture experiment, not production Ada code.

## Questions

1. Can the containerized PydanticAI adapter reach the existing host Ollama instance on the target Mac?
2. Does the same Qwen3 tool-call path show material latency regression in the container?
3. What is the approximate steady-state memory of the initialized Ada/PydanticAI container process?

This probe does **not** benchmark Docker Desktop's entire Linux-VM baseline overhead. It measures the Ada container itself and end-to-end tool-call latency. If these results are already unacceptable, the container-first option fails early; if acceptable, Docker Desktop's host-level overhead remains an operational consideration rather than an architecture blocker.

## Build

From this directory:

```bash
docker build -t ada-container-probe .
```

The image uses Python 3.14 and pins:

```text
pydantic-ai-slim[openai]==2.46.0
```

## Benchmark

Run with the intended hardened baseline:

```bash
docker run --rm \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --pids-limit=128 \
  --memory=1g \
  --cpus=2 \
  -e ADA_OLLAMA_MODEL=ada-qwen3-8b-4k \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 \
  ada-container-probe
```

Expected validation:

- exactly one tool call per measured run;
- all outputs valid;
- compare median/mean with the native PydanticAI baseline:
  - native mean: **7.720 s**
  - native median: **7.720 s**

Do not over-interpret small timing differences.

## Idle container memory

Start the initialized container without making a model request:

```bash
docker run -d \
  --name ada-container-probe-idle \
  --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --pids-limit=128 \
  --memory=1g \
  --cpus=2 \
  -e ADA_OLLAMA_MODEL=ada-qwen3-8b-4k \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434/v1 \
  ada-container-probe \
  python idle_probe.py
```

Confirm readiness:

```bash
docker logs ada-container-probe-idle
```

Then capture one stats snapshot:

```bash
docker stats --no-stream ada-container-probe-idle
```

Finally:

```bash
docker rm -f ada-container-probe-idle
```

## Security properties exercised

The probe intentionally runs:

- as a non-root user;
- without Linux capabilities;
- with no-new-privileges;
- with a read-only root filesystem;
- without host filesystem mounts;
- without Docker socket access;
- with PID, memory and CPU limits.

No authoritative Ada Memory is mounted.

## Interpretation

### Pass

- host Ollama is reachable;
- all tool calls are valid;
- container latency remains in the same practical range as native;
- initialized container memory is modest relative to the M1/16 GB target.

### Fail / re-open

- host Ollama cannot be reached without weakening the isolation model;
- latency materially regresses;
- the container cannot operate with the intended hardening flags;
- memory/CPU overhead is large enough to interfere with normal family-laptop use.
