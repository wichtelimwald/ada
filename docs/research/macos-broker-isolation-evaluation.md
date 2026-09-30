# MVP-30 S2 macOS broker-isolation evaluation

Status: target-Mac decision evidence for proposed ADR-0011  
Date: 2026-09-28

## Question

Which macOS enforcement mechanism can keep Ada's ordinary runtime from directly
reading an unrelated unlocked Memory vault or retrieving its vault secret while
still allowing authorized human editing and a broker-mediated access path?

This is the hard gate at the start of MVP-30 S2. It is deliberately narrower than
the complete broker implementation.

## Required invariants

A viable mechanism must prove on the target Mac that:

1. an ordinary Ada runtime process cannot directly read an unrelated unlocked
   plaintext vault;
2. that runtime cannot retrieve the unrelated vault's decryption secret;
3. an authorized human can still edit the intended unlocked Markdown surface;
4. the broker can perform its scoped operation without giving the runtime a vault
   root, mount point, key or bearer capability;
5. secrets do not appear in command arguments, environment variables, repository
   files, logs or model context.

The first two are negative tests. A design that only encrypts at rest is not enough.

## Platform evidence

### Mounted encrypted images

The current macOS disk-image interface supports AES-128/AES-256 encryption and
password input on stdin. The current manual recommends `diskutil image` as the
preferred interface for multiple formerly-`hdiutil` operations, so Ada must keep
the command behind a platform adapter rather than make a binary name architectural.

Evidence:

- https://keith.github.io/xcode-man-pages/hdiutil.1.html

The same manual also documents an important isolation detail: disk images can mount
with file ownership ignored. When owners are ignored, permissions do not provide
the intended user separation. S2 probes therefore explicitly request owners to be
honored and must not treat the default disk-image mount behavior as a security
boundary.

### Separate POSIX service identity

A system-domain launchd job can run under a configured `UserName`/`GroupName`.
That gives S2 a credible Unix identity boundary for filesystem access, but it implies
a privileged/system service installation rather than an ordinary per-user
LaunchAgent.

Evidence:

- https://keith.github.io/xcode-man-pages/launchd.plist.5.html
- https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html

This is a candidate, not an adopted decision. In particular, Keychain availability
and restart/unlock behavior for a headless service identity still have to be proven.

### Legacy macOS Keychain ACLs

macOS keychain items outside the data-protection/iCloud-keychain model can carry
ACLs with trusted applications. Apple documents that when an operation is
restricted and the caller is not trusted, macOS may ask the user to Deny, Allow or
Always Allow access.

Evidence:

- https://developer.apple.com/documentation/security/access-control-lists
- https://developer.apple.com/documentation/security/secaccesscreate(_:_:_:)
- https://keith.github.io/xcode-man-pages/security.1.html

That means a legacy trusted-application ACL is **not by itself a fail-closed process
isolation primitive** for Ada: an untrusted same-user process may reach an
authorization prompt, and a mistaken "Always Allow" can widen future access.

There is an additional problem for Ada's current Python development shape:
path/application-based trust cannot safely distinguish two scripts if broker and
ordinary runtime are both represented by the same Python interpreter executable.
S2 must not "secure" a secret by trusting a shared Python executable.

### Data-protection Keychain access groups

Apple documents keychain access groups as code-signing/entitlement-backed app
identity. A macOS app has a private default access group, and another app cannot
claim that identity simply by naming it; restricted entitlements are protected by
the signing/provisioning model.

Evidence:

- https://developer.apple.com/documentation/security/sharing-access-to-keychain-items-among-a-collection-of-apps
- https://developer.apple.com/documentation/technotes/tn3125-inside-code-signing-provisioning-profiles

This is a stronger candidate for broker-only secret retrieval than legacy ACL
prompts, but it introduces a signed-binary/app identity and packaging dependency.
It therefore needs a target-Mac proof before Ada commits to it during an MVP that is
currently developed as a Python CLI.

### App Sandbox

Apple describes the macOS App Sandbox as kernel-enforced resource restriction.
Sandboxing the ordinary runtime is therefore another technically credible way to
deny direct filesystem access while a broker helper owns narrower privileges.

Evidence:

- https://developer.apple.com/documentation/xcode/configuring-the-macos-app-sandbox

The cost is significant: it couples S2 to a signed macOS application/service shape
and entitlement/IPC design earlier than the current MVP otherwise requires. It also
does not directly solve the future Linux/server deployment path.

## Candidate matrix

| Candidate | Vault isolation | Secret isolation | Human editing | MVP cost | Current status |
| --- | --- | --- | --- | --- | --- |
| Same user + Unix socket only | No | No proven isolation | Yes | Low | Rejected as enforcement boundary |
| Same user + legacy Keychain trusted-app ACL | No for mounted vault | Prompt-based, not fail-closed; shared-interpreter problem | Yes | Low/medium | Insufficient alone |
| Distinct runtime/service POSIX identity + filesystem ownership/ACL | Credible; must be target-Mac-proven with owners enabled | Separate-account Keychain/service bootstrap unresolved | Yes, if human/broker permissions are explicit | Medium; system service/admin install | Probe first for filesystem boundary |
| Sandboxed ordinary runtime + privileged/signed broker helper | Credible | Credible with signed keychain identity/access group | Yes | High; packaging/signing/entitlements | Keep as strong fallback |
| Signed broker helper + data-protection Keychain access group, runtime otherwise same user | Does not by itself isolate mounted vault | Credible | Yes | Medium/high | Secret-only candidate; needs another vault boundary |

## S2 probe sequence

### Probe A — encrypted vault mechanics and same-user baseline

Use `research/memory/mvp-30-s2/probe_encrypted_vault.py`.

The probe:

- creates only synthetic data in a temporary directory;
- creates an AES-256 APFS sparse bundle without putting the passphrase in argv,
  environment variables, files or output;
- attaches it with ownership enabled;
- proves that another process under the **same** user can read the unlocked
  plaintext file;
- detaches and reattaches the image and verifies persistence;
- optionally, when an explicit existing runtime account is supplied and
  non-interactive sudo is already authorized, proves whether that distinct identity
  is denied direct read access.

A same-user read succeeding is an **expected negative result**: it is evidence that
"separate process" is not a storage isolation boundary.

### Probe B — choose the identity model

After Probe A, run a focused target-Mac comparison between:

1. a distinct POSIX runtime/service identity with explicit vault ownership/ACL; and
2. a signed/sandboxed runtime + signed broker-helper model.

Do not add a production broker daemon yet.

Decision criteria:

- negative read must fail for the ordinary runtime;
- authorized human editing must still work;
- unattended restart must be explainable and testable;
- no broad root/all-user capability;
- installation/maintenance burden must be acceptable for the MVP;
- the design should not make a future Linux service impossible.

### Probe C — Keychain secret isolation

Only after the process identity model is narrowed, test secret storage using the
matching mechanism:

- distinct service identity: prove the runtime account cannot access the broker
  account's chosen keychain item and prove broker restart/unlock behavior;
- signed broker identity: prove a data-protection Keychain item/private access group
  is retrievable by the broker helper but denied to the ordinary runtime without a
  user authorization escape hatch.

Legacy `security -T`/trusted-application ACLs may be useful characterization
evidence, but do not satisfy the hard gate by themselves because an untrusted app
can trigger user confirmation.

## Decision rule

Do not implement `EncryptedVaultProvider` or production IPC until one candidate
passes both required negative tests on the target Mac.

If no candidate does so without unacceptable packaging/security cost, revise
ADR-0011 rather than weakening the requirement.

## Current conclusion

Target-Mac evidence now supports the smallest credible S2 enforcement candidate:

- keep broker + human-editing context under the logged-in user;
- run the ordinary/model-facing runtime under a distinct restricted OS identity;
- expose only broker-mediated scoped operations to that runtime.

Probe A proved that same-user process separation is insufficient. Probe B then
proved that a distinct OS identity can be denied both direct access to the unlocked
synthetic vault and retrieval of the synthetic Keychain item while the logged-in
broker/user context retains both.

This selects the **candidate isolation direction**, not the final packaged topology.
A dedicated Ada runtime identity, startup/launchd ownership, IPC authentication,
restart behavior, and ordinary-runtime resource needs still require explicit design
and validation before production broker code is accepted.


## Target-Mac Probe A result

Maintainer run on macOS 26.6.2 arm64, Python 3.14.6:

- AES-256/APFS sparse-bundle create/attach/detach/reattach: **PASS**;
- synthetic current data survives detach/reattach: **PASS**;
- cleanup: **PASS**;
- second process under the same macOS user can read the unlocked synthetic file:
  **YES**;
- mounted volume root observed as uid 501, gid 20, mode 0755.

This closes one question: a separate Ada process under the same login user is not
an enforceable Memory-domain boundary once a vault is unlocked.

The observed root mode also confirms that S2 must verify effective mounted
ownership/modes at runtime instead of assuming image-creation mode flags become the
mounted volume-root permissions.

## Refined KISS candidate after Probe A

The simplest credible macOS topology is now worth probing in the **opposite**
direction from a privileged broker daemon:

- keep the broker in the logged-in user's context, where human editing and the
  user's Keychain are naturally available;
- run the ordinary Ada runtime/model-facing process under a separate restricted
  OS identity;
- let that restricted runtime request scoped operations over a broker IPC boundary;
- do not give the restricted runtime the vault root, mount point or key.

Why this candidate moved forward:

- Apple documents that the data-protection Keychain is available only in a user
  context, not to a system launchd daemon;
- a launchd system-domain job can run under a configured `UserName`/`GroupName`;
- therefore keeping the broker in the user's context avoids inventing a headless
  Keychain-unlock scheme, while a restricted runtime identity can still provide the
  filesystem boundary Probe A proved is missing from same-user process separation.

This is still a probe candidate, not an adopted architecture. It changes the
question from "how does a broker daemon access a user's Keychain?" to "can a
restricted runtime identity still perform everything the ordinary runtime needs
while being denied direct Memory/Keychain access?"

Relevant Apple evidence:

- TN3137: programs outside a user context, such as launchd daemons, cannot use the
  data-protection Keychain; each logged-in user has their own user-context keychain.
- launchd supports system-domain services running under an explicit `UserName` /
  `GroupName`.
- launchd-managed agents remain in the logged-in user context.

## Probe B — restricted runtime identity

Probe B should use an existing unprivileged system identity only as a **temporary
stand-in**; it must not create users or install launchd jobs.

It must prove:

1. the current logged-in user can read/edit the mounted synthetic vault;
2. a distinct unprivileged identity cannot read the synthetic private file;
3. the logged-in user can create/read a synthetic Keychain item without exposing
   its value in argv/environment/files/logs;
4. the distinct runtime identity cannot retrieve that item;
5. all synthetic Keychain state and mounts are removed after the probe.

A pass would justify a later dedicated Ada runtime service-account/install probe.
It would **not** yet prove final IPC authentication, packaging, startup, or resource
access for the real runtime.


## Target-Mac Probe B result

Maintainer run on macOS 26.6.2 arm64 against PR #47 head `1027234`:

Prepare:

- broker/current-user synthetic vault read: **PASS**;
- broker/current-user synthetic Keychain read: **PASS**;
- workspace created under cross-identity-traversable `/tmp`;
- no compiler/Xcode dependency;
- no automatic sudo use.

Restricted identity check, executed explicitly as existing account `nobody`:

```text
probe=mvp-30-s2-restricted-runtime-manual
runtime_user=nobody
vault_read_exit=1
keychain_read_exit=44
```

Interpretation:

- direct read of the unlocked synthetic private file: **DENIED**;
- retrieval of the synthetic Keychain item: **DENIED**.

Cleanup:

- Keychain cleanup: **PASS**;
- vault detach cleanup: **PASS**;
- workspace cleanup: **PASS**.

The probe also exposed and fixed two research-harness defects before accepting the
result:

1. macOS per-user `/var/folders/.../T` caused a false denial before the restricted
   identity reached the intended targets, so Probe B now uses explicit `/tmp`;
2. the cleanup state initially tracked the mounted slice instead of the whole disk
   image device, so detach now records/selects the whole `/dev/diskN` device and
   is regression-tested.

These fixes are part of the evidence quality: only the final rerun above is treated
as isolation evidence.
