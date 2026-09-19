# ADR-0003: Start Ada as a container-first modular monolith

- **Status:** Accepted
- **Date:** 2026-09-20

## Context

Ada needs an execution topology that preserves the modularity strategy from ADR-0002 while remaining practical for:

- the initial MacBook Air M1 / 16 GB target;
- one to two evenings per week of development and maintenance;
- local-first operation;
- future Linux/server deployment;
- reproducible development and runtime environments;
- explicit security/privacy boundaries;
- external, human-editable authoritative Memory.

The following alternatives were evaluated:

1. native Python modular monolith;
2. container-first Python modular monolith;
3. split trusted Ada core and agent runtime;
4. polyglot/service-oriented architecture from the start.

Agreed decision weights:

| Criterion | Weight |
| --- | ---: |
| Maintainer simplicity / lifetime operational burden | 15% |
| Security / host privilege boundary | 20% |
| Reproducible installation / deployment | 15% |
| Portability / future Linux-server path | 15% |
| Resource overhead on M1 / 16 GB | 15% |
| Native host integration | 5% |
| Lock-in / replaceability | 15% |

Final research scores:

| Option | Score |
| --- | ---: |
| **Container-first modular monolith** | **85** |
| Split trusted core / agent runtime | 77 |
| Native Python modular monolith | 76 |
| Polyglot services | 59 |

## Terminology

In this ADR, **modular monolith** means:

> one initial Ada application process / deployable unit with strict internal module and port boundaries.

It does **not** mean:

- one giant module;
- shared global state across capabilities;
- direct coupling between integrations;
- one framework owning all features;
- inability to replace components.

Modularity is defined by Ada-owned ports and dependency direction, not by process count.

## Target-Mac evidence

The selected topology was tested on the target MacBook Air M1 / 16 GB with the same PydanticAI/Qwen3 tool-call path used in ADR-0002 research.

Native PydanticAI:

- mean: **7.720 s**
- median: **7.720 s**

Containerized PydanticAI:

- measured: **7.808 / 7.794 / 7.790 s**
- mean: **7.797 s**
- median: **7.794 s**
- all tool calls/results valid: yes

The median delta was **+0.074 s (~+0.96%)**, which is not material for the tested path.

An initialized container process used approximately **66.68 MiB** and one PID.

A one-shot CPU sample captured around startup/import activity is not treated as steady-state idle evidence. Background CPU remains something to measure on the real long-running runtime.

The probe also validated operation with:

- non-root user;
- dropped Linux capabilities;
- `no-new-privileges`;
- read-only root filesystem;
- no host filesystem mounts;
- no Docker socket;
- PID, memory and CPU limits;
- host Ollama reached through a configurable endpoint.

## Decision

Ada starts as a **Python-first, container-first modular monolith**.

The initial topology is:

```text
host operating system
├── authoritative Memory (outside Ada runtime)
├── local model runtime / Ollama
└── Ada runtime container
     └── one Ada application process
          ├── Ada core/domain
          ├── application/use cases
          ├── Ada Guard
          ├── Action Ledger
          ├── Ada-owned ports
          └── replaceable adapters
               └── PydanticAI initially
```

## Modularity and capability growth

Ada must remain able to add or replace capabilities independently.

Examples:

- Email and WhatsApp are different `MessageChannelPort` adapters.
- PydanticAI and a future agent framework are different `AgentRuntimePort` adapters.
- Calendar providers are different `CalendarPort` adapters.
- Memory backends remain behind the later Memory boundary.

A newly installed or discovered adapter, plugin, MCP server, or tool receives **no consequential authority automatically**.

Activation, data access and grants remain explicit Ada decisions.

### In-process first, isolate by risk

Trusted, low-risk adapters may run in the main Ada process initially.

If a capability later introduces materially higher risk or a distinct privilege/lifecycle requirement, it may move behind the same Ada-owned port into a separate process or container.

Examples that may justify isolation later:

- shell/code execution;
- browser/computer control;
- untrusted third-party plugins;
- risky native parsers;
- multi-user remote hosting;
- capabilities needing materially different host privileges.

This allows Ada's topology to evolve without changing domain semantics or unrelated adapters.

## Development container vs runtime container

Ada uses the Dev Container approach for reproducible development, but a Dev Container is **not** the production deployment artifact.

The project should use a shared build/dependency foundation with separate profiles or stages:

```text
shared container/dependency foundation
        |
        +--> development target
        |      + .devcontainer/devcontainer.json
        |      + development tools
        |      + writable source workspace
        |
        +--> runtime target
               + runtime dependencies only
               + hardened runtime settings
```

Development-only tools, credentials and privileges must not leak into the runtime image.

## Runtime security constraints

The default runtime profile must:

- run as a non-root user;
- never require `--privileged`;
- never mount the Docker socket;
- avoid Docker-in-Docker;
- drop unneeded Linux capabilities, preferably all by default;
- use `no-new-privileges`;
- retain a restrictive seccomp profile;
- use a read-only root filesystem where practical;
- provide only narrow explicit writable/cache locations;
- avoid broad host filesystem mounts;
- expose only explicit network ports;
- support CPU, memory and PID limits;
- use native arm64/multi-arch images rather than amd64 emulation on Apple Silicon.

A container is defense in depth, not Ada's authorization model.

## Authoritative Memory

Authoritative Memory remains **outside** the Ada runtime/container.

The invariant is:

`container lifecycle != Memory lifecycle`

Therefore:

- Memory is not baked into the image;
- Memory is not stored only in the container writable layer;
- a Docker named volume must not become the only human-accessible authoritative copy;
- Ada does not mount the user's entire home directory;
- the first vertical slice uses no authoritative Memory mount.

The later Memory ADR will decide whether Ada uses a narrow external bind mount or a stronger host-side Memory broker/API.

## Ollama / local model runtime

For the initial macOS target, Ollama remains outside the Ada container.

Ada reaches it through a configurable endpoint; Docker Desktop's `host.docker.internal` path is one implementation detail for local macOS development/runtime.

No domain code may depend on that hostname.

Later Linux/server deployments may use another host endpoint or a separate container/network topology without changing the agent-runtime port.

## Consequences

### Positive

- one simple initial application process;
- strong internal modularity and replaceability;
- reproducible Python/Linux runtime;
- better host isolation than direct native execution;
- clean future Linux/server path;
- low measured Ada-process memory;
- no meaningful measured tool-call latency penalty;
- capability-specific sandboxing can be added later without redesigning the core.

### Negative

- a compatible container runtime becomes an installation prerequisite;
- Docker Desktop or equivalent adds host-level resource overhead;
- macOS-native APIs/files are less direct from the container;
- bind mounts require careful least-privilege design;
- process isolation between trusted core and runtime is not present by default;
- resource and background CPU behavior must still be measured during real long-running use.

## Alternatives considered

### Native Python modular monolith

Remains a credible fallback with the lowest runtime overhead and easiest macOS integration.

Not selected because it provides weaker host isolation and less reproducible installation/deployment while offering little measured performance benefit for the tested agent path.

### Split trusted core / agent runtime

Offers the strongest immediate process boundary.

Not selected for the MVP because IPC, lifecycle, serialization and recovery complexity are introduced before a current capability requires them.

It remains the preferred escalation pattern for high-risk capabilities.

### Polyglot/service-oriented architecture

Not selected.

Multiple language ecosystems and service boundaries create too much operational and maintenance burden for the current project stage.

A future adapter may still use another language when a concrete capability justifies it.

## Re-open triggers

Re-open this ADR if:

- container-runtime overhead becomes unacceptable on the M1 / 16 GB target;
- native macOS integration becomes central and cannot be cleanly exposed through a narrow adapter;
- a supported container runtime cannot maintain the intended security profile;
- installation feedback shows container prerequisites are materially harder than a native package;
- authoritative Memory cannot be integrated without granting excessive filesystem authority;
- a future capability requires a stronger process boundary;
- the modular ports fail to keep adapter/framework replacement bounded;
- a selected dependency requires host behavior fundamentally incompatible with the container profile.

## Follow-up

After the architecture-doc PR stack is merged:

1. create the implementation scaffold;
2. add a shared multi-stage container build;
3. add a Dev Container configuration;
4. implement the first vertical slice from the representative scenarios;
5. keep production provider integrations and authoritative Memory out of that first slice;
6. validate local startup, tests, and the hardened runtime profile.
