# Ada-only KDBX vault — manual experimental test

**Research-only. No actual IONOS/Untis passwords yet.**

1. Install KeePassXC separately on macOS (operator-managed). Choose a test
   directory inside the **existing persistent Ada Memory root**, e.g.
   `<memory-root>/secrets/`. Use KeePassXC to create
   `<memory-root>/secrets/ada.kdbx` with **KDBX4/Argon2** and a
   synthetic test master passphrase. Do not add a key file. Create a
   synthetic entry with title `ionos/calendar` and an arbitrary fake password.

2. Ensure the file is owned only by the operator (`chmod 600` on macOS).
   The PoC refuses symlinks, oversize vaults and group/world-readable files.

3. In the Ada repo root, with Docker Desktop running, execute:

```sh
# Set this to your actual local Memory root, not a Git project checkout.
export ADA_MEMORY_ROOT="/absolute/path/to/ada-memory"

docker build --target secrets-poc -t ada-secrets-poc .

docker run --rm -it --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges \
  --mount "type=bind,source=$ADA_MEMORY_ROOT,target=/ada-memory,readonly" \
  ada-secrets-poc secrets-check --memory-root /ada-memory
```

The password prompt runs **inside the foreground Ada CLI process**, from a
terminal. The passphrase is not passed via Docker arguments, environment
variables or a network channel. The command reports only whether decryption
succeeded and then **closes** the vault. It does *not* unlock a background Ada
runtime. If Docker cannot read the host-owned 0600 file using its non-root
Ada UID, investigate Docker Desktop's bind-mount permissions instead of
weakening file permissions or running Ada as root.

4. Repeat with an incorrect passphrase, without a terminal, and after a
   second run. The wrong passphrase must produce a generic failure without
   revealing user names or titles. No network is needed.

5. If using `FileMemoryStore`, the Memory Git repo's local
   `.git/info/exclude` ignores `/secrets/`. Do not force-add vaults to Git;
   check `git -C "$ADA_MEMORY_ROOT" ls-files -- secrets` is empty.
   Back up the encrypted KDBX file separately, preserving ownership/mode.
   The master passphrase must be recoverable by the operator.

## Not yet tested

Container build and real KeePassXC KDBX4 interoperability must be run on the
target Mac. Python 3.14 compatibility and distribution licensing are open gates.

**No live account migration or provider wiring is part of this test.**
