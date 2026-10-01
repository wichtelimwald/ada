# MVP-30 S2 target-Mac probes

This directory contains **research-only** probes for MVP-30 S2. They use synthetic
data and do not implement the production Memory Broker or
`EncryptedVaultProvider`.

Decision evidence lives in:

- `docs/research/macos-broker-isolation-evaluation.md`
- `docs/decisions/ADR-0011-memory-broker-protection.md`

## Probe A — encrypted vault mechanics

Run on the target Mac from the repository root:

```bash
python3 research/memory/mvp-30-s2/probe_encrypted_vault.py
```

Expected result:

- `status: ok`
- `same_user_unlocked_read: true`
- `detach_reattach_persistence: true`
- `cleanup: true`

The same-user read is intentionally expected to succeed. It demonstrates that a
separate process running as the same macOS user is **not** an isolation boundary
for an already-unlocked mounted vault.

The script:

- creates a temporary AES-256 APFS sparse bundle;
- keeps its random passphrase only in process memory;
- passes the passphrase to `hdiutil` via stdin, never argv/environment/files/output;
- mounts with `-owners on`;
- writes only a synthetic marker;
- detaches, reattaches, verifies persistence, then cleans up.

No real Memory or credential is used.

## Optional distinct-identity read probe

If there is already a suitable non-privileged test account, the same script can
also check whether that account can directly read the mounted synthetic file:

```bash
sudo -v
python3 research/memory/mvp-30-s2/probe_encrypted_vault.py \
  --runtime-user <existing-test-account>
```

The script itself never prompts for sudo and never creates/deletes users. It first
uses non-interactive `sudo -n`; if authorization is unavailable, that sub-probe is
reported as skipped.

For a candidate distinct-runtime-identity design, expected evidence is:

- `distinct_user_probe: "executed"`
- `distinct_user_unlocked_read: false`

Do **not** treat a skipped result as security evidence.

## Not covered by Probe A

Probe A does not prove:

- Keychain isolation;
- broker IPC authentication;
- service startup/restart behavior;
- human-editor access under a final identity/ACL layout;
- protection of Git metadata/history;
- production suitability of `hdiutil`.

Those belong to later S2 probes after the process identity model has been narrowed.

## Safety

- synthetic data only;
- temporary directory only;
- no account creation or system configuration;
- no secret in argv/environment/log output;
- cleanup runs in a `finally` block;
- no third-party dependency or binary is installed/executed.


## Probe B — restricted runtime identity

Probe B tests the refined KISS candidate: keep broker + human editing in the
logged-in user context and run the ordinary runtime/model-facing process under a
distinct restricted OS identity.

**The Python probe never invokes `sudo`.** It only prepares synthetic test state,
prints one exact identity-switch command, and later cleans up unprivileged.

### 1. Prepare — no admin rights

```bash
python3 research/memory/mvp-30-s2/probe_restricted_runtime.py prepare
```

Expected preparation evidence:

- `status: "ready"`
- `broker_user_vault_read: true`
- `broker_user_keychain_read: true`
- one `manual_identity_switch_command`
- one `cleanup_command`

Review the printed command before running it.

### 2. Run exactly one explicit identity-switch command

First invalidate any existing sudo credential cache:

```bash
sudo -k
```

Then run **only** the exact `manual_identity_switch_command` printed by the
prepare step. It has this shape:

```bash
sudo -u nobody -- /bin/sh /tmp/ada-mvp30-s2-identity-.../restricted-check.sh
```

This use of `sudo` is solely for the OS identity switch. The tested child process
runs as the restricted account, not as root/admin.

Expected output:

- `vault_read_exit` is non-zero;
- `keychain_read_exit` is non-zero.

Immediately invalidate the sudo credential cache again:

```bash
sudo -k
```

### 3. Cleanup — no admin rights

Run the exact `cleanup_command` printed by the prepare step. It has this shape:

```bash
python3 research/memory/mvp-30-s2/probe_restricted_runtime.py cleanup \
  /tmp/ada-mvp30-s2-identity-.../probe-state.json
```

Expected cleanup evidence:

- `keychain_cleanup: true`
- `vault_cleanup: true`
- `workspace_cleanup: true`
- `status: "ok"`

The probe:

- creates no users;
- installs no launchd service;
- never calls `sudo` itself;
- requires no Xcode/Swift compiler;
- stores only synthetic data;
- sends the synthetic Keychain value to macOS `security -i` only over stdin,
  never argv/environment/files/output;
- uses an existing `nobody` / `_nobody` account by default only as a temporary
  stand-in for a future restricted Ada runtime identity.

A pass justifies a later dedicated service-account/launchd installation probe. It
does not yet accept final IPC, packaging, startup, or resource-access topology.


## Probe C / S2C1 — Unix peer identity

This probe validates the local IPC authentication boundary before any permanent
runtime account or launchd service is installed.

It uses macOS `getpeereid(3)` on an AF_UNIX/SOCK_STREAM connection. The broker
checks the kernel-supplied peer UID before reading request payload.

### 1. Prepare — no admin rights

```bash
python3 research/memory/mvp-30-s2/probe_ipc_peer_identity.py prepare
```

Prepare automatically starts a short-lived broker probe and connects once as the
current user. Because the configured stand-in runtime identity is different, that
connection must be rejected **without sending or parsing request payload**.

Expected preparation evidence includes:

- `status: "ready"`
- `wrong_user_rejected: true`
- `wrong_user_sent_payload: false`
- one `manual_identity_switch_command`
- one `collect_command`

The server self-times out after 90 seconds if the restricted client is never run.

### 2. Run exactly one explicit identity switch

As with Probe B, clear any existing sudo timestamp first, run only the printed
command, then invalidate the timestamp immediately:

```bash
sudo -k
# run the exact manual_identity_switch_command printed by prepare
sudo -k
```

Expected restricted-client result:

```json
{"auth":"accepted","response":"OK","status":"ok"}
```

The Python probe itself never invokes sudo.

### 3. Collect and clean up — no admin rights

Run the exact `collect_command` printed by prepare.

A pass requires:

- at least one wrong peer UID rejected;
- rejection occurred before request payload read;
- accepted peer UID exactly equals the configured restricted runtime UID;
- accepted payload is the synthetic `PING`;
- workspace cleanup succeeds.

This proves IPC peer-identity enforcement only. It does not create or validate the
final dedicated Ada runtime user or launchd lifecycle.
