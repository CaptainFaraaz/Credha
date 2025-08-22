FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY credit_intel/pyproject.toml /app/
RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

COPY credit_intel /app/credit_intel

EXPOSE 8501
CMD ["streamlit", "run", "credit_intel/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]