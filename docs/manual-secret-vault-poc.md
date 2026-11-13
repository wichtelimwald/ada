# Ada-only KDBX vault — manual experimental test

**Research-only. No actual IONOS/Untis passwords yet.**

1. Decide which persistent Ada Memory root to use. `<memory-root>` is
   a placeholder, **not** a directory Ada creates for this experiment. If you
   already configured an Ada Memory root, use exactly that path. Otherwise,
   the following is an **example location for the PoC only**, not an
   established project default. Run once on the Mac:

```sh
export ADA_MEMORY_ROOT="$HOME/ada-memory"
umask 077
mkdir -p "$ADA_MEMORY_ROOT/secrets"
chmod 700 "$ADA_MEMORY_ROOT/secrets"
```

   Keep the `ADA_MEMORY_ROOT` value for the Docker command below. Do not put
   this directory inside the Ada **source-code** repository.

2. Install KeePassXC separately on macOS (operator-managed), then use it to
   create `$ADA_MEMORY_ROOT/secrets/ada.kdbx` with **KDBX4/Argon2** and a
   synthetic test master passphrase. Do not add a key file. Create a synthetic
   entry with title `ionos/calendar` and an arbitrary fake password.
   Afterwards run `chmod 600 "$ADA_MEMORY_ROOT/secrets/ada.kdbx"`.
   The PoC refuses symlinks, oversize vaults and group/world-readable files.

3. In the Ada **source-code** repository root, with Docker Desktop running
   and the `ADA_MEMORY_ROOT` environment variable set as above, execute:

```sh
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

5. If using `FileMemoryStore`, the initialized Memory Git repo's
   local `.git/info/exclude` ignores `/secrets/`. Do not force-add vaults
   to Git; **if the Memory root contains a `.git` directory**, check
   `git -C "$ADA_MEMORY_ROOT" ls-files -- secrets` is empty.
   Back up the encrypted KDBX file separately, preserving ownership/mode.
   The master passphrase must be recoverable by the operator.

## Not yet tested

Container build and real KeePassXC KDBX4 interoperability must be run on the
target Mac. Python 3.14 compatibility and distribution licensing are open gates.

**No live account migration or provider wiring is part of this test.**
