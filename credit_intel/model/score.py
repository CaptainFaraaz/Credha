from __future__ import annotations
import json
from datetime import datetime
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from credit_intel.db import models
from credit_intel.features.compute import compute_features_for_issuer
from credit_intel.model.persistence import load_model
from credit_intel.utils.logging import get_logger

logger = get_logger(__name__)


def score_latest(db: Session, issuer_id: int, ticker: str) -> models.Score | None:
    model_info = load_model(ticker)
    if model_info is None:
        logger.warning(f"No model found for {ticker}; computing features and skipping scoring")
        compute_features_for_issuer(db, issuer_id)
        return None
    model, feature_names = model_info
    feats = compute_features_for_issuer(db, issuer_id)
    if not feats:
        return None
    X = np.array([[feats.get(name, 0.0) for name in feature_names]])
    if hasattr(model, "predict_proba"):
        prob_stress = float(model.predict_proba(X)[0, 1])
    else:
        prob_stress = float(model.decision_function(X))
    creditworthiness = float(max(0.0, min(100.0, 100.0 - prob_stress * 100.0)))

    contributions = {name: 0.0 for name in feature_names}
    try:
        import shap  # optional
        background = np.array([X[0]])
        explainer = shap.KernelExplainer(lambda z: model.predict_proba(z)[:, 1], background)
        shap_vals = explainer.shap_values(X, nsamples=100)
        contributions = {name: float(val) for name, val in zip(feature_names, shap_vals[0])}
    except Exception:
        pass

    summary = (
        f"Score reflects recent returns ({feats.get('ret_7d'):.2%}/{feats.get('ret_30d'):.2%}), volatility ({feats.get('vol_30d'):.4f}), "
        f"drawdown ({feats.get('dd_90d'):.2%}), macro (VIX {feats.get('vix'):.2f}, UST10Y {feats.get('ust10y'):.2f}), "
        f"and news sentiment (avg {feats.get('sentiment_mean'):.2f})."
    )

    rec = models.Score(
        issuer_id=issuer_id,
        as_of=datetime.utcnow(),
        score=creditworthiness,
        contributions_json=json.dumps(contributions),
        summary=summary,
    )
    db.add(rec)
    db.commit()
    return rec