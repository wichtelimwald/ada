# Duckling characterization — operational result

- **Date:** 2026-09-20
- **Target:** MacBook Air M1
- **Pinned upstream commit:** 59a13ff87b1aa8be6b93d387244f8636b26185c5
- **Result:** build failed before semantic characterization

## Failure

The pinned upstream Dockerfile uses:

- `haskell:8-buster` for the builder stage;
- `debian:buster` for the runtime stage.

The runtime image failed during:

~~~text
apt-get update
apt-get install libpcre3 libgmp10
~~~

with exit code 100.

Debian 10 / Buster is now an archived distribution rather than a current Debian release. Making this Dockerfile build reliably would therefore require Ada research to modify archive sources and/or modernize the base images and dependency set.

## Decision relevance

This is not treated as a semantic failure of Duckling.

It is, however, direct operational/maintenance evidence:

- the current pinned upstream container path is not reproducibly buildable on the Ada target without modification;
- the integration requires a separate Haskell/service runtime;
- the upstream Dockerfile itself carries an obsolete Debian base;
- evaluating Duckling semantics would first require Ada-owned build-system maintenance unrelated to Ada's product value.

For the current Ada scope and maintenance budget, this materially lowers Duckling's runtime/packaging and operational-complexity scores.

## Decision

Do **not** patch the Duckling Dockerfile merely to force a semantic benchmark at this stage.

Duckling remains a reference benchmark and a possible future replacement if:

- Quickadd/ctparse becomes unmaintainable;
- a maintained Duckling packaging/runtime path becomes available;
- or Ada's temporal requirements outgrow the selected Python-native approach.

The existing evidence is sufficient to reject Duckling as the preferred initial resolver on operational-fit grounds, not on licensing or temporal-quality grounds.
