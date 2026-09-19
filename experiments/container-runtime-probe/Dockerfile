FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYDANTIC_AI_NO_BANNER=1

RUN useradd --create-home --uid 10001 ada

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY container_benchmark.py idle_probe.py ./

USER ada

CMD ["python", "container_benchmark.py"]
