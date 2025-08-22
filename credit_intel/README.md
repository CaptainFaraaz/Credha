# Credit Intel (Prototype)

Real-Time Explainable Credit Intelligence Platform prototype.

## Features
- Ingests structured data (Yahoo Finance prices; macro proxies VIX, UST10Y)
- Ingests unstructured data (public RSS feeds) with event typing and sentiment
- Computes engineered features and trains a simple interpretable classifier
- Scores issuers with feature-level SHAP contributions and summaries
- FastAPI backend + Streamlit dashboard
- Dockerized for quick run

## Quickstart (Docker)

```bash
docker compose -f credit_intel/docker-compose.yml up --build
```

Then open:
- API: http://localhost:8000/health
- Dashboard: http://localhost:8501

Click "Refresh Now" in the dashboard to populate data.

## Local Run (Dev)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -e credit_intel/
uvicorn credit_intel.api.main:app --reload
# in another terminal
streamlit run credit_intel/dashboard/app.py
```

## Architecture
- `ingestion/structured.py`: yfinance for prices and macro proxies
- `ingestion/unstructured.py`: RSS parsing, rule-based event typing, VADER sentiment
- `features/compute.py`: feature derivation and snapshot persistence
- `model/train.py`: heuristic labels for stress; LogisticRegression + SHAP
- `model/score.py`: scoring with SHAP KernelExplainer if needed
- `api/main.py`: endpoints to refresh, retrieve scores, features, events
- `scheduler/refresh.py`: periodic refresh via APScheduler
- `db/models.py`: SQLAlchemy models

## Explainability
- Uses SHAP values mapped directly to model features
- Displays per-feature contribution bars and plain-language summary

## Trade-offs
- Heuristic labels approximate credit risk; replace with labeled defaults/downgrades
- RSS mapping to issuers is simplistic; extend with NER and linkers
- VADER sentiment is light-weight; can upgrade to domain-tuned models

## Configuration
- Env vars: `CI_TICKERS`, `DATABASE_URL`, `DATA_REFRESH_MINUTES`, `MODEL_DIR`

## License
Prototype for demonstration.