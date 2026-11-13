FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYDANTIC_AI_NO_BANNER=1

RUN groupadd --gid 10001 ada \
    && useradd --uid 10001 --gid 10001 --create-home ada

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src

FROM base AS development

# File-native Memory history and its tests require the Git CLI.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --editable /app \
    && mkdir -p /workspace \
    && chown ada:ada /workspace

WORKDIR /workspace
USER ada
CMD ["sleep", "infinity"]

FROM base AS secrets-poc

# Experimental KDBX compatibility/interactive-unlock test only.
# The wheel hashes are verified only for CPython 3.14 on Linux/aarch64.
COPY requirements/kdbx-py314-linux-aarch64.txt /app/requirements/kdbx-py314-linux-aarch64.txt
RUN python -c "import platform, sys; sys.exit(0 if sys.version_info[:2] == (3, 14) and platform.machine() == 'aarch64' else 'KDBX PoC requires CPython 3.14/Linux aarch64')" \
    && python -m pip install --no-cache-dir /app \
    && python -m pip install --no-cache-dir --only-binary=:all: \
        --require-hashes --force-reinstall \
        -r /app/requirements/kdbx-py314-linux-aarch64.txt

USER ada
ENTRYPOINT ["python", "-m", "ada"]
CMD ["doctor"]

FROM base AS runtime

RUN python -m pip install --no-cache-dir /app

USER ada
ENTRYPOINT ["python", "-m", "ada"]
CMD ["doctor"]
