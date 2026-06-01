#FROM ubuntu:latest
#LABEL authors="NAGARAJ ROLLI"
#
#ENTRYPOINT ["top", "-b"]

# Stage 1: Build virtual environment dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final runtime image execution
FROM python:3.11-slim AS runner

WORKDIR /app

# Non-root security best practice for production containers
RUN groupadd -g 999 appuser && useradd -r -u 999 -g appuser appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY ./src /app/src

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main.app", "--host", "0.0.0.0", "--port", "8000"]
