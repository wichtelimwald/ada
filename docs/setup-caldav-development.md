# MVP-60 S6 — Local IONOS CalDAV development configuration

**Status:** configuration/Keychain foundation only. This does **not** enable
a live Ada calendar or authorize real writes. The durable-state purge,
operation-record identity, provider privilege diagnostics and opt-in real
provider acceptance are still outstanding (MVP-60 S6/S7).

## Mac host setup (non-sensitive test calendar only)

Prerequisite: Ada's own IONOS Mail Business mailbox with a dedicated CalDAV
application password in the **macOS Keychain**. Do not paste credentials into
chat, GitHub, files, shell arguments or environment variables.

1. Create `~/.config/ada/caldav.toml` on the Mac host (not in the repo):

   ```toml
   version = 1
   mailbox = "ada@example.invalid"
   base_url = "https://dav.mailbusiness.ionos.de"

   [[calendar]]
   id = "family"
   collection = "/caldav/REPLACE-WITH-TEST-CALENDAR-ID/"
   audience = "family"
   access = "write"
   ```

   Replace the illustrative mailbox and test collection ID **locally** with
   your configured Ada account and a deliberately non-sensitive test calendar.
   The config is data only; `access = "write"` is **not** an AdaGuard grant.
   A permissioned action path must not be enabled merely because this is set.

2. Restrict the local configuration to its owner:

   ```bash
   chmod 600 ~/.config/ada/caldav.toml
   ```

   The loader refuses group/world permissions, symlinks, invalid paths,
   unknown configuration keys (including `password`) and any CalDAV
   destination other than the pinned HTTPS IONOS origin.

3. If not already set up for the prior IONOS probe, add the dedicated app
   password to **Keychain on the Mac**. The command prompts for it; do not
   include the password in the command itself:

   ```bash
   security add-generic-password -s ada-caldav -a '<ada-mailbox-address>' -w
   ```

   The service `ada-caldav` intentionally matches the existing probe.
   The only password read path uses `/usr/bin/security find-generic-password`
   and suppresses command output/errors in diagnostics.

## Execution boundary

`load_ionos_development_settings` parses this TOML on macOS or Linux;
`build_development_ionos_adapter` composes the existing provider adapter
and retrieves the password from macOS Keychain **without contacting IONOS**.
The adapter is not connected to Ada's CLI or email channel yet.

The Dev Container runs Linux and **cannot access the Mac Keychain**. Never
copy a real app password into that container. Unit tests use synthetic
`example.invalid` credentials and an injected fake transport.

Provider credentials may also give access to Ada's mailbox. Until S6
protects DBOS durable payloads and S7 verifies real-provider semantics,
**do not start live create/update/cancel operations** with this configuration.
