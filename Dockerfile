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

RUN python -m pip install --no-cache-dir --editable /app \
    && mkdir -p /workspace \
    && chown ada:ada /workspace

WORKDIR /workspace
USER ada
CMD ["sleep", "infinity"]

FROM base AS runtime

RUN python -m pip install --no-cache-dir /app

USER ada
ENTRYPOINT ["python", "-m", "ada"]
CMD ["doctor"]
