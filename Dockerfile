FROM golang:1.24 AS mox-builder

ENV CGO_ENABLED=0

RUN GOBIN=/tmp/go-bin go install github.com/mjl-/mox@latest

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=mox-builder /tmp/go-bin/mox /usr/local/bin/mox

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --no-cache-dir .

CMD ["uvicorn", "openmailserver.app:app", "--host", "0.0.0.0", "--port", "8787"]
