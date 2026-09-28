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
