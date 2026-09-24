# httpx2 direct transport: focused adoption review

- **Date:** 2026-09-23
- **Scope:** Ada's first loopback-only Ollama chat profile, Python 3.14;
  dependency adoption in source and local builds. This is not an approval to
  redistribute an Ada-built container or installer.

## Why a direct pin

Ada must prevent ambient proxy variables from routing local prompts to another
service. PydanticAI 2.46.0's Ollama provider accepts an injected asynchronous
HTTP client. The pinned `pydantic-ai-slim` metadata already requires
`httpx2>=2.7`; the resolved OpenAI client also requires `httpx2>=2.12,<3`.
Ada now imports `httpx2` itself to supply an `AsyncClient(trust_env=False)`.
Declaring the exact version prevents an unreviewed transport update from
changing this privacy boundary. The standard-library readiness check still
uses `urllib` with proxy discovery disabled; the model call uses PydanticAI's
existing client interface. A regression test exercises the **real** provider
against local Ollama and proxy listeners, including a persistent connection.

Avoiding the direct requirement would leave `httpx2` installed transitively
but would not pin the transport that Ada constructs and tests. Replacing
PydanticAI's client interface with custom networking would increase the
integration and maintenance burden for this narrow use case.

## Provenance, maintenance, and security

- Upstream is the [Pydantic-maintained HTTPX2 project](https://github.com/pydantic/httpx2),
  a fork of HTTPX. Its [changelog](https://github.com/pydantic/httpx2/blob/main/src/httpx2/CHANGELOG.md)
  records version 2.13.1 on 2026-09-23. This is an active but relatively new
  stewardship arrangement; recheck before an upgrade.
- Upstream provides a [private vulnerability reporting route and published
  advisories](https://github.com/pydantic/httpx2/security). As checked on
  2026-09-23, its five listed advisories affect `httpx2` versions below
  2.10.0, 2.11.0 or 2.12.0; one also affects `httpcore2` below 2.10.0.
  Both installed versions are 2.13.1. This is a review of the published
  advisories, not proof that unknown vulnerabilities do not exist.
- For this profile, `trust_env=False` ignores ambient proxy and certificate
  environment settings for the client, per [upstream documentation](https://pydantic.dev/docs/httpx2/api/environment_variables/).
  Ada validates the endpoint as loopback before constructing the provider,
  does not follow redirects in its readiness check, and closes the client on
  CLI exit. The model client processes conversation contents locally and
  contacts the configured loopback service. The client library is general
  purpose; these constraints apply to **this Ada use**, not every use of it.
  The native chat process still has its macOS user's permissions; direct
  transport only constrains this client's configured model traffic (see
  [threat model](../security/threat-model.md)).

## License and artifact evidence

- The [upstream license](https://github.com/pydantic/httpx2/blob/main/LICENSE.md)
  is BSD-3-Clause, including both Encode and Pydantic copyright holders. It
  permits use and redistribution with its copyright/license/disclaimer retained
  in source or binary distribution materials and forbids implied endorsement.
  This is compatible with Ada's MIT-owned source; it does not relicense httpx2.
- In the Ada-only Linux x86_64 Python 3.14.7 environment resolved on
  2026-09-23, installed `httpx2==2.13.1` reports BSD-3-Clause and includes
  `httpx2-2.13.1.dist-info/licenses/LICENSE.md`. Its `WHEEL` metadata says
  `Root-Is-Purelib: true`, `Tag: py3-none-any`; the installed file inventory
  contains no `.so`, `.dylib`, or `.dll` files. Its required `httpcore2==2.13.1`
  likewise includes a BSD-3-Clause license file and no such native files.
  Other required packages include `anyio`, `idna`, and `truststore`; optional
  CLI, HTTP/2, SOCKS, WebSocket, compression, and Emscripten extras are not
  activated by this direct requirement. These observations apply to this
  installed environment, not every platform artifact or entire Ada graph.
- Ada currently distributes project source, the dependency manifest, and a
  Dockerfile for local builds; it does not publish a prebuilt runtime image or
  installer. Source release still needs the Ada-only graph and notices checked
  as stated in [NOTICE](../../NOTICE.md). Publishing built artifacts requires
  exact wheel hashes, per-platform license inventories, copyright notices,
  bundled-library checks, and source/NOTICE obligations. The separate
  [release-input gate](https://github.com/wichtelimwald/ada/pull/33) is still
  pending and deliberately fails until those inputs exist. A version pin is
  not a hash lock or a redistribution clearance.

**Re-open when:** PydanticAI changes its client contract, httpx2/httpcore2 is
upgraded, a new relevant advisory appears, the endpoint ceases to be local, or
Ada publishes a prebuilt artifact.
