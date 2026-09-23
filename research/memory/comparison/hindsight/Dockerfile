FROM python:3.14-slim

ARG HOST_UID=1000
ARG HOST_GID=1000

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgssapi-krb5-2 \
    && if ! getent group "$HOST_GID" >/dev/null; then groupadd --gid "$HOST_GID" ada-research; fi \
    && GROUP_NAME="$(getent group "$HOST_GID" | cut -d: -f1)" \
    && if ! getent passwd "$HOST_UID" >/dev/null; then useradd --uid "$HOST_UID" --gid "$GROUP_NAME" --create-home ada-research; fi \
    && rm -rf /var/lib/apt/lists/*
