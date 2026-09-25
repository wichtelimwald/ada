# Technology evaluation — Execution topology and container boundary

**Status:** Research complete — decision evidence supports ADR-0003  
**Date checked:** 2026-09-19  
**Depends on:** ADR-0002 and `docs/architecture/modular-core-boundaries.md`

**Update (2026-09-24):** This is historical topology research. Its
`host.docker.internal` Ollama path assumes the host service is reachable beyond
loopback and is not the first macOS chat configuration. ADR-0003 and ADR-0006
now specify native `ada chat` with loopback-bound Ollama and the bridged Dev
Container for development and tests. Containerized local chat needs a separate
restricted connection and review.

## 1. User need

Ada needs an execution architecture that:

- remains understandable and maintainable with roughly one to two evenings per week of development capacity;
- runs locally on the initial MacBook Air M1 / 16 GB target;
- keeps the accepted modular Ada-owned boundaries;
- makes development and installation reproducible;
- improves isolation from the host where practical;
- preserves the option of later Linux/server deployment;
- keeps authoritative human-editable memory outside Ada's runtime/container.

The goal is not to introduce microservices or containers for their own sake.

## 2. Scope and constraints

### Must have

- PydanticAI can be used as the initial replaceable agent-runtime adapter.
- The first coherent implementation may be Python-first.
- Ada Guard, Action Ledger, provider ports and domain semantics remain Ada-owned.
- Local Ollama remains usable on the M1/16 GB target.
- The architecture must not require macOS-only process semantics.
- Authoritative memory is not stored in the container image or an opaque container-only volume.
- Containers, if used, must not require privileged mode, Docker-socket access, or broad host filesystem access.
- Deleting/recreating the Ada runtime must not delete authoritative memory.
- Project-owned code remains intended to use MIT.
- No mandatory cloud infrastructure.

### Nice to have

- one-command local startup after prerequisites;
- the same dependency lock and Linux userspace for contributors and deployed runtime;
- explicit CPU/RAM limits so Ada yields the shared laptop;
- easy later deployment to a Linux vServer;
- development tooling isolated from the host.

### Non-goals

- Kubernetes;
- distributed microservices;
- high availability;
- containerizing Ollama merely for architectural symmetry;
- treating a container as Ada's permission/security model;
- deciding the final Memory implementation in this ADR.

### Cross-capability integration assumptions

- **Runtime/process topology:** one Ada application process is preferred until a real privilege or lifecycle boundary justifies another process.
- **IPC/API expectations:** no internal network API is required between Ada core and PydanticAI in the first slice.
- **Packaging/distribution:** a production OCI-compatible image may become the primary reproducible runtime artifact; a Dev Container may share the same base but is development-specific.
- **Startup/background operation:** explicit start/stop is sufficient for the MVP; always-on daemon behavior is not required.
- **Shared resources:** Ollama/model memory is expected to dominate runtime resource use; avoid duplicating the model inside the Ada container.
- **External memory:** when Memory is implemented, it remains host/operator-owned and directly editable outside Ada.

## 3. Important distinction: Dev Container vs runtime image

A Dev Container is a **development environment definition**, not by itself a production deployment architecture.

The Dev Container specification explicitly allows development-specific tools and metadata that should not necessarily exist in a deployed image.

Ada should therefore use a shared container build foundation with separate targets/profiles:

```text
Dockerfile / dependency lock
        |
        +--> development target
        |      + .devcontainer/devcontainer.json
        |      + editor/dev tools
        |      + writable source workspace
        |
        +--> runtime target
               + only runtime dependencies
               + hardened container settings
               + no source-tooling assumptions
```

This gives reproducibility without shipping compilers, editor tooling, or development credentials in the deployed runtime.

## 4. Alternatives

### A — Native Python modular monolith

Run one Python Ada process directly on macOS for the MVP.

```text
macOS
├── Ada Python process
├── Ollama
└── external Memory
```

**Advantages**

- lowest runtime overhead;
- easiest access to native macOS resources;
- simplest debugging;
- no container prerequisite.

**Disadvantages**

- Python/system dependency setup leaks onto the host;
- weaker filesystem/process isolation;
- installation becomes more sensitive to host Python/tool versions;
- future Linux/server reproducibility requires more packaging discipline;
- dependency/runtime experiments share the family laptop's host environment.

### B — Container-first Python modular monolith

Run one Python Ada process inside a hardened Linux container; keep Ollama on the host initially.

```text
macOS
├── external Memory (host-owned)
├── Ollama (host)
└── container runtime / Linux VM
     └── Ada
          ├── Ada Core
          └── PydanticAI adapter
```

The Ada container talks to host Ollama through a configurable model endpoint. On Docker Desktop for macOS, `host.docker.internal` provides this path.

**Advantages**

- reproducible Python/Linux environment;
- simpler contributor onboarding and eventual server deployment;
- meaningful additional host isolation on macOS because Docker Desktop containers run inside a Linux VM;
- easy start/stop/recreate semantics;
- CPU/RAM/PID limits can protect the shared laptop;
- PydanticAI remains an in-process adapter, so there is no premature IPC layer;
- compatible with a Dev Container development workflow.

**Disadvantages**

- Docker/compatible runtime becomes an additional prerequisite;
- Docker Desktop itself has resource overhead;
- bind mounts weaken isolation for every mounted host directory;
- native macOS integrations are less direct;
- containers are not a substitute for Ada Guard or data-access policy.

**Current research preference:** strongest starting option, subject to agreed criteria/weights.

### C — Split trusted Ada core and agent runtime

Run Ada core/Guard/Ledger in one trusted process and PydanticAI/model-facing orchestration in a separate container/process.

```text
trusted Ada core
   ^        |
   | IPC    | typed proposals/results
   v        |
agent-runtime container
```

**Advantages**

- stronger process boundary around model-facing dependencies;
- the agent-runtime process can be denied direct access to provider credentials and authoritative memory files;
- attractive later if Ada gains browser/shell/code-execution or third-party plugin capabilities.

**Disadvantages**

- IPC protocol, serialization, lifecycle, versioning and failure handling become Ada responsibilities immediately;
- duplicates part of the architecture already provided by typed in-process boundaries;
- complicates debugging and recovery before evidence shows the boundary is necessary;
- higher maintenance cost for the MVP.

**Current interpretation:** useful escalation path, not the starting topology.

### D — Polyglot / service-oriented architecture from the start

Use Python for PydanticAI plus separate Rust/Swift/other services for trusted core, UI, connectors or policy.

**Advantages**

- components can use platform-specialized languages;
- process/language boundaries can enforce some isolation.

**Disadvantages**

- largest build, packaging, IPC and maintenance burden;
- multiple dependency ecosystems;
- very poor fit with the current maintainer/time budget;
- architecture complexity arrives before product evidence requires it.

**Current interpretation:** reject for MVP unless a later capability provides a concrete reason.

## 5. Container security boundary

A container is useful defense in depth, not Ada's root of trust.

### Required runtime defaults if option B is accepted

- run as a non-root application user;
- never use `--privileged`;
- never mount `/var/run/docker.sock`;
- no Docker-in-Docker;
- drop Linux capabilities not required by Ada, ideally `--cap-drop=ALL`;
- use `no-new-privileges`;
- keep Docker's default seccomp profile;
- use a read-only root filesystem where the runtime permits it;
- provide explicit temporary/cache locations rather than making the whole filesystem writable;
- publish only explicit Ada ports and bind local-only services to loopback where practical;
- add CPU, RAM and PID limits after measuring the first slice;
- use arm64/multi-arch images on Apple Silicon rather than relying on amd64 emulation.

The development container may need a writable workspace and development-only tools. It must still avoid privileged mode and Docker-socket access unless a future reviewed development workflow demonstrates an unavoidable need.

## 6. External authoritative memory

The container decision must not move authoritative Memory inside Ada.

### Baseline rule

```text
container lifecycle != memory lifecycle
```

Authoritative memory remains in an operator-owned location outside the image/container and must be readable/editable without Ada.

### Do not do

- do not bake memory into the image;
- do not store authoritative memory only in the container writable layer;
- do not make a Docker named volume the only human-accessible copy;
- do not mount the user's whole home directory;
- do not mount broad document folders merely for convenience.

### Initial integration options for the later Memory ADR

**Narrow host bind mount**

Mount exactly one configured host memory directory into Ada.

Pros:
- simplest;
- human-editable;
- survives container replacement.

Cons:
- the container receives the permissions granted to that mount;
- a read/write mount allows compromised in-container code to modify those files.

**Host-side Memory broker**

Keep files entirely outside the Ada runtime container and expose a narrow local API to Ada.

Pros:
- stronger technical boundary around raw files;
- agent/runtime dependencies need not receive filesystem access.

Cons:
- adds a second process, IPC, lifecycle and another component to maintain.

**Current position:** do not choose between these before the Memory ADR. The first vertical slice needs no authoritative-memory mount at all.

## 7. Ollama / model placement

For the initial Mac:

```text
Ada container --> host.docker.internal:11434 --> host Ollama
```

Reasons:

- the existing local model installation remains usable;
- no model duplication in container storage;
- model lifecycle remains independent from Ada;
- Ada's model endpoint stays configurable;
- later Linux/server deployments can point the same adapter at a host service or another container/network endpoint.

Ada must not hard-code `host.docker.internal` into domain code.

## 8. Installation and distribution implications

A container-first architecture can reduce Ada-specific installation steps, but it does not make installation dependency-free.

Users still need:

- a compatible container runtime;
- Ollama/local model installation for the selected local-model profile;
- external provider credentials/integrations;
- an external memory location once Memory is implemented.

Docker Desktop is one macOS option, but Ada should not make Docker Desktop itself a product requirement. Docker Desktop has separate commercial subscription terms for larger organizations; Ada should target OCI/Docker-compatible artifacts and keep runtime-specific assumptions narrow.

A future friendly install may wrap these prerequisites, but that is outside the current MVP.

## 9. Agreed decision criteria

Weights were agreed with the maintainer before scoring.

| Criterion | Weight | Why it matters |
| --- | ---: | --- |
| Maintainer simplicity / lifetime operational burden | 15% | One to two evenings per week penalizes unnecessary IPC and multi-service overhead. |
| Security / host privilege boundary | 20% | Ada processes untrusted content and will eventually hold consequential credentials. |
| Reproducible installation / deployment | 15% | A public project needs a tractable setup beyond one developer machine. |
| Portability / future Linux-server path | 15% | Avoid a permanent macOS-only architecture without a concrete benefit. |
| Resource overhead on M1 / 16 GB | 15% | Ada shares the family laptop and must yield resources. |
| Native host integration | 5% | Containers can make macOS-native APIs and files less convenient. |
| Lock-in / replaceability | 15% | Ada must be able to replace channels, providers, runtimes, and implementation frameworks without redesigning the core. |
| **Total** | **100%** | |

## 9a. "Modular monolith" means deployment topology, not architecture coupling

In this evaluation, **monolith** means one initial Ada application process / deployable unit.

It does **not** mean:

- one giant module;
- shared global state across capabilities;
- direct dependencies between every feature;
- a single framework owning all integrations;
- inability to replace components.

The intended structure is:

```text
Ada process
├── stable Ada core/domain
├── application/use-case layer
├── ports
│   ├── AgentRuntimePort
│   ├── MessageChannelPort        (when first channel is implemented)
│   ├── CalendarPort
│   ├── TravelTimePort
│   ├── SchedulerPort             (when required)
│   └── MemoryPort                (after Memory ADR)
└── adapters
    ├── PydanticAI runtime
    ├── Email channel
    ├── future WhatsApp channel
    ├── calendar provider
    └── other selected components
```

Replacing one adapter must not require changes to unrelated domain logic.

Examples:

- email → WhatsApp changes a channel adapter, not the authority model;
- PydanticAI → another runtime changes the AgentRuntimePort implementation, not Ada Guard or Action Ledger;
- one calendar provider → another changes CalendarPort implementation, not conflict-domain logic.

### Capability growth model

Ada is expected to gain capabilities over time.

For low-risk, trusted capabilities, an adapter may run in-process for simplicity.

A future third-party plugin mechanism must **not** mean arbitrary downloaded Python code automatically executes inside Ada's trusted process. Higher-risk or less-trusted extensions may require an out-of-process/container sandbox behind the same Ada-owned port.

Therefore topology can evolve per capability:

```text
today:
Ada process -> in-process trusted adapter

later, if risk requires:
Ada process -> same port -> isolated capability process/container
```

This is the key reason to keep topology and modularity separate decisions.

### Discovery / registration rule

Adapter availability may be discovered for usability, but **privileged capability activation is explicit**.

A newly installed channel, tool, MCP server, or plugin must not gain consequential authority through automatic discovery. It must receive explicit configuration and the applicable Ada grants.

## 10. Evidence summary before scoring

| Question | A Native monolith | B Container-first monolith | C Split core/runtime | D Polyglot services |
| --- | --- | --- | --- | --- |
| Simple initial code path | strongest | strong | weaker | weakest |
| Host isolation | weakest | good defense in depth | strongest of MVP-realistic options | potentially strong |
| Reproducible environment | adequate with uv | strong | strong but complex | complex |
| Future Linux/server | possible | strong | strong | strong |
| M1 resource overhead | lowest | moderate | higher | highest |
| Native macOS access | strongest | weaker | mixed | mixed |
| External memory compatible | yes | yes | yes | yes |
| Requires IPC now | no | no | yes | yes |
| Matches maintainer capacity | strong | strong | weak | poor |

## 10a. Evidence-based scoring

Scale:

- **5 — Excellent:** strongly satisfies the criterion with little compensation.
- **4 — Good:** solid fit with bounded trade-offs.
- **3 — Adequate:** workable but meaningful cost/compensation remains.
- **2 — Weak:** significant mismatch or ongoing burden.
- **1 — Poor:** fundamentally unattractive for this criterion.

| Criterion | Weight | A Native Python | B Container-first modular monolith | C Split core/runtime | D Polyglot services |
| --- | ---: | ---: | ---: | ---: | ---: |
| Maintainer simplicity | 15% | **4** | **4** | 2 | 1 |
| Security / host boundary | 20% | 2 | **4** | **5** | 4 |
| Reproducible install/deploy | 15% | 3 | **5** | 4 | 3 |
| Portability / Linux server | 15% | 4 | **5** | **5** | 4 |
| M1 / 16 GB resource use | 15% | **5** | 3 | 3 | 2 |
| Native host integration | 5% | **5** | 3 | 3 | 4 |
| Lock-in / replaceability | 15% | **5** | **5** | 4 | 3 |
| **Weighted total / 100** | **100%** | **76** | **85** | **77** | **59** |

### Score rationale

**A — Native Python (76):** simplest and cheapest at runtime, excellent native integration, and still highly modular if Ada ports are respected. It loses mainly on host isolation and reproducible deployment.

**B — Container-first modular monolith (85):** preserves the same in-code modularity while adding a reproducible Linux runtime and useful host defense in depth. Its main cost is Docker/VM resource overhead and weaker direct macOS integration.

**C — Split core/runtime (77):** strongest security boundary, but the immediate IPC/lifecycle burden is not justified by the current MVP. It remains an important escalation path for riskier capabilities.

**D — Polyglot services (59):** flexible in theory but creates too much packaging, IPC, dependency, and maintenance overhead before Ada has evidence that separate languages/services are needed.

The score does **not** imply that option B's single process is less modular than C or D. Replaceability comes from Ada-owned ports and dependency direction, not process count.

## 11. Target-Mac prototype evidence

The remaining B-vs-A uncertainties were tested on the target MacBook Air M1 / 16 GB using the same local PydanticAI/Qwen3 tool-call path used in ADR-0002 research.

### Container profile

The probe successfully ran with:

- non-root application user;
- `--cap-drop=ALL`;
- `no-new-privileges`;
- read-only root filesystem;
- tmpfs-only writable temporary space;
- no host filesystem mounts;
- no Docker socket;
- PID, memory and CPU limits;
- host Ollama reached through a configurable endpoint.

### Latency

Native PydanticAI baseline:

- mean: **7.720 s**
- median: **7.720 s**

Containerized PydanticAI:

- warm-up: **13.756 s**
- measured: **7.808 / 7.794 / 7.790 s**
- mean: **7.797 s**
- median: **7.794 s**
- all tool calls/results valid: yes

Measured median difference: **+0.074 s (~+0.96%)**.

This is not a material runtime regression for the tested path.

### Container-process memory

One initialized idle-probe container reported:

- memory: **66.68 MiB / 1 GiB**
- PIDs: **1**

This is modest relative to the 16 GB target.

A one-shot CPU sample showed 71.35%, but it was captured around startup/import activity and is **not treated as steady-state idle CPU evidence**. Real idle/background CPU should be measured later against the actual long-running Ada runtime.

The resource score therefore remains 3 rather than being raised: the Ada process itself is small, but Docker Desktop / the Linux VM has its own host-level baseline overhead that this probe did not attempt to eliminate.

### Prototype conclusion

Option B passes the target-machine gate:

- host Ollama connectivity works;
- intended hardening flags work;
- request latency is effectively equivalent to native execution;
- Ada/PydanticAI process memory is modest;
- no authoritative Memory mount is required.

No evidence from the prototype justifies preferring native execution over container-first for the initial topology.

Split-process IPC was not prototyped because option C did not become the preferred score and no current MVP capability requires that added complexity.

## 12. Final recommendation

The agreed weighting plus target-Mac evidence supports:

> **Python-first modular monolith, container-first runtime, Dev Container for development, host Ollama initially, external authoritative Memory outside the container.**

This is intentionally a **modular monolith**, not a microservice architecture. The single-process topology is a KISS starting point; capability replaceability is enforced through Ada-owned ports.

Use one process until a capability introduces a real reason to isolate it, such as:

- general shell/code execution;
- browser/computer control;
- untrusted third-party plugins;
- high-risk document parsers/native libraries;
- multi-user remote hosting;
- a component that needs materially different privileges or lifecycle.

At that point, move the capability behind an existing Ada-owned port into a separate sandbox/process rather than redesigning the whole system.

## 13. Decision handoff

Record the following in ADR-0003:

> **Ada starts as a Python-first, container-first modular monolith.**

Meaning:

- one initial Ada application process/deployable unit;
- strict Ada-owned ports and dependency direction;
- PydanticAI as the replaceable runtime adapter;
- a Dev Container for development and a separate hardened runtime image/profile;
- host Ollama initially on macOS;
- authoritative Memory outside the container;
- no broad host mounts;
- no privileged mode or Docker socket;
- risk-driven capability isolation later behind existing Ada-owned ports.

The container is defense in depth, not the permission model.

## 14. Re-open triggers

Re-open the topology/container decision if:

- Docker/compatible-runtime overhead is unacceptable on the M1/16 GB target;
- native macOS integration becomes central to the MVP and cannot be cleanly reached from the container;
- a supported container runtime cannot provide the required local isolation;
- future privileged capabilities require a stronger process boundary;
- external Memory cannot be integrated without granting the main runtime too much filesystem authority;
- installation feedback shows the container prerequisite is harder than a native package;
- PydanticAI or a selected component requires host behavior that materially conflicts with the container profile.

## Primary references

- Dev Container specification and metadata reference: https://containers.dev/ and https://github.com/devcontainers/spec
- Docker bind mounts: https://docs.docker.com/engine/storage/bind-mounts/
- Docker runtime security options: https://docs.docker.com/reference/cli/docker/container/run
- Docker seccomp: https://docs.docker.com/engine/security/seccomp/
- Docker resource constraints: https://docs.docker.com/engine/containers/resource_constraints/
- Docker Desktop macOS permissions/isolation: https://docs.docker.com/desktop/setup/install/mac-permission-requirements/
- Docker Desktop networking: https://docs.docker.com/desktop/features/networking/networking-how-tos/
- Docker Desktop macOS installation/licensing: https://docs.docker.com/desktop/setup/install/mac-install/
