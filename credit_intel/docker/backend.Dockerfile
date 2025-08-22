FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY credit_intel/pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

COPY credit_intel /app/credit_intel

EXPOSE 8000
CMD ["uvicorn", "credit_intel.api.main:app", "--host", "0.0.0.0", "--port", "8000"]