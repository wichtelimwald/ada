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

## Recommended: VS Code Dev Container

The repository has an **opt-in** configuration
`.devcontainer/secrets-poc/devcontainer.json`. The normal development
configuration does not mount the vault or install the experimental reader.

1. Open the PR branch in VS Code. Use **Dev Containers: Reopen Folder Locally**
   if you are currently inside a container, then **Dev Containers: Reopen in
   Container** and select **Ada (KDBX research)**.
2. This profile mounts **only**
   `$HOME/ada-memory/secrets` read-only as `/ada-memory/secrets`. If your
   actual Mac directory differs, update the `mounts` source in the optional
   profile **before reopening**. Do not mount your personal password manager.
3. In the integrated VS Code terminal (inside the container), run:

```sh
python -m ada secrets-check --memory-root /ada-memory
```

   This is the already-tested one-shot check. For the **in-process lifecycle**
   the existing local chat also supports:

```sh
python -m ada chat --unlock-vault
```

   The second command needs a working **local Ollama endpoint reachable from
   that exact container** before it prompts. If Ollama is not reachable from
   the dev container, do not relax the loopback-only transport restriction:
   run the focused synthetic lifecycle tests instead.

```sh
python -m unittest tests.test_kdbx_secrets -v
```

   The chat process holds the unlocked vault for its own lifetime and closes
   it on exit; however, **no live calendar/mail adapter consumes credentials
   yet**. No general Ada background service is started by VS Code.

## Alternate: isolated manual Docker smoke check

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

## Evidence and remaining gates

The maintainer reported (2026-11-13) the correct-passphrase case successfully
opened a real KeePassXC KDBX file inside the manually started test container
and the incorrect-passphrase case failed closed. The tested image digest and
exact code revision were not recorded, so this is **operator-reported smoke
evidence**, not repeatable exact-head validation.

The VS Code profile, full test suite and in-process chat unlock still require
target-Mac verification. Dependency/release review and the integration with
real IONOS/mail consumers remain open gates.

**No live account migration or provider wiring is part of this test.**
