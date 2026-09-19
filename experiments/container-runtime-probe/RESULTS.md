# Results — Container runtime probe

**Status:** Executed successfully on target MacBook Air M1 / 16 GB.

## Environment

- target: MacBook Air M1 / 16 GB
- containerized Python: 3.14
- PydanticAI: 2.46.0
- model: `ada-qwen3-8b-4k`
- Ollama: host process reached through `host.docker.internal:11434`

## Containerized PydanticAI benchmark

- warm-up: **13.756 s**
- measured runs: **7.808 / 7.794 / 7.790 s**
- mean: **7.797 s**
- median: **7.794 s**
- all valid: yes
- exactly one tool call per measured run: yes

Native comparison:

- mean: **7.720 s**
- median: **7.720 s**

Observed steady-state median delta:

- absolute: **+0.074 s**
- relative: **~+0.96%**

This is not a material latency regression for the tested path.

## Idle initialized container

`docker stats --no-stream` snapshot:

- CPU: **71.35%**
- memory: **66.68 MiB / 1 GiB**
- memory percentage: **6.51%**
- network I/O: **690 B / 84 B**
- block I/O: **0 B / 0 B**
- PIDs: **1**

### CPU caveat

The single CPU snapshot was captured immediately around startup/import activity and is not treated as a reliable steady-state idle CPU measurement.

The memory result is still useful: the initialized Ada/PydanticAI process used about **66.7 MiB** inside the container, which is modest relative to the 16 GB target.

Steady-state idle CPU should be measured later against the real long-running Ada runtime rather than repeated as an architecture-gate microbenchmark.

## Security-profile result

The benchmark successfully ran with:

- non-root image user;
- `--cap-drop=ALL`;
- `--security-opt=no-new-privileges`;
- read-only root filesystem;
- tmpfs-only writable temporary area;
- no host filesystem mounts;
- no Docker socket;
- PID limit;
- 1 GiB memory limit;
- 2 CPU limit.

No authoritative Ada Memory was mounted.

## Conclusion

The container-first option passes the target-machine probe.

For the tested local tool-call path:

- host Ollama connectivity works without weakening the intended container profile;
- latency is effectively equivalent to the native baseline;
- initialized Ada/PydanticAI process memory is modest;
- the intended hardening flags are compatible with the runtime.

No evidence from this probe justifies preferring native execution over the container-first modular-monolith option.

The CPU snapshot is intentionally not used as steady-state evidence.
