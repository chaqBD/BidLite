"""
BidLite Predictive Analytics Engine
=====================================
Two complementary price-prediction models are blended into a single estimate:

  1. Ridge Regression (Feature-Based)
     Extracts numeric cable features (size, conductors, material, quantity)
     and trains a regularised linear model using Leave-One-Out cross-validation
     so every prediction is genuinely out-of-sample.

  2. Qdrant KNN Regression (Vector-Based)  ← the novel part
     For each item we query Qdrant for its K semantic nearest neighbours
     and return a similarity-weighted average price.  This is Qdrant used as
     an ML prediction engine, not just a search index.

  3. Ensemble
     Simple average of the two models.  When both agree the confidence is high;
     when they diverge the item is flagged as uncertain / needing clarification.
"""

import re
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import r2_score, mean_absolute_percentage_error
from dotenv import load_dotenv

load_dotenv()

# ── AWG / KCMIL → mm² lookup (NEC to IEC) ────────────────────────────────────
_AWG_TO_MM2 = {
    "12": 3.3, "10": 5.3, "8": 8.4, "6": 13.3, "4": 21.2, "3": 26.7,
    "2": 33.6, "1": 42.4, "1/0": 53.5, "2/0": 67.4, "3/0": 85.0, "4/0": 107.0,
}
_KCMIL_TO_MM2 = 0.5067  # 1 kcmil = 0.5067 mm²


# ── Feature extraction ────────────────────────────────────────────────────────

def _parse_size_mm2(desc: str) -> float | None:
    d = str(desc).lower()

    # IEC mm² already in description
    m = re.search(r"(\d+(?:\.\d+)?)\s*mm", d)
    if m:
        return float(m.group(1))

    # KCMIL
    m = re.search(r"(\d+)\s*k?cmil", d)
    if m:
        return round(float(m.group(1)) * _KCMIL_TO_MM2, 1)

    # AWG  e.g. "#1/0", "1/0 AWG", "#10"
    m = re.search(r"#?(\d+/\d+|\d+)\s*awg", d)
    if m:
        return _AWG_TO_MM2.get(m.group(1))

    m = re.search(r"#(\d+/\d+|\d+)", d)
    if m:
        return _AWG_TO_MM2.get(m.group(1))

    return None


def extract_features(item_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return a numeric feature DataFrame aligned with item_df.index.
    Columns: size_mm2, n_conductors, is_al, is_armoured, is_earth, log_qty
    """
    desc = item_df["description"].astype(str).str.lower()

    feats = pd.DataFrame(index=item_df.index)

    # Cross-sectional area — strongest price predictor
    feats["size_mm2"] = item_df["description"].apply(_parse_size_mm2).astype(float)
    median_size = feats["size_mm2"].median()
    feats["size_mm2"] = feats["size_mm2"].fillna(median_size if not np.isnan(median_size) else 50.0)

    # Conductor count  (1C, 3C, 3C+E …)
    n_cond = desc.str.extract(r"(\d+)\s*c[\s,\+]")[0].astype(float)
    feats["n_conductors"] = n_cond.fillna(1.0)

    # Material
    feats["is_al"] = desc.str.contains(r"\bal\b|alumin", regex=True, na=False).astype(float)

    # Armoured
    feats["is_armoured"] = desc.str.contains(r"swa|armou?r", regex=True, na=False).astype(float)

    # Earth / ground
    feats["is_earth"] = desc.str.contains(r"earth|ground|g/y", regex=True, na=False).astype(float)

    # Quantity (log scale — economics of scale)
    feats["log_qty"] = np.log1p(item_df["qty"].fillna(1).astype(float))

    return feats.astype(float)


# ── Model 1: Ridge regression with LOO-CV ─────────────────────────────────────

def ridge_predict(item_df: pd.DataFrame) -> pd.DataFrame:
    """
    Train Ridge regression on item-level mean prices.
    Every prediction is out-of-sample (Leave-One-Out CV).

    Returns item_df enriched with:
      ridge_pred, ridge_low, ridge_high, ridge_error_pct
    """
    result = item_df.copy()

    X = extract_features(item_df).values
    y = np.log1p(item_df["mean_price"].values)   # log-transform for linear fit

    scaler = StandardScaler()
    X_s = scaler.fit_transform(X)

    model = Ridge(alpha=0.5)
    loo = LeaveOneOut()
    preds = np.zeros(len(y))

    for tr, te in loo.split(X_s):
        model.fit(X_s[tr], y[tr])
        preds[te] = model.predict(X_s[te])

    result["ridge_pred"]  = np.expm1(preds)
    mae = np.median(np.abs(result["ridge_pred"] - result["mean_price"]))
    result["ridge_low"]   = (result["ridge_pred"] - 1.5 * mae).clip(lower=0)
    result["ridge_high"]  = result["ridge_pred"] + 1.5 * mae
    result["ridge_error_pct"] = (
        (result["ridge_pred"] - result["mean_price"]) / result["mean_price"] * 100
    ).round(2)

    # Full-data fit for coefficients (display only)
    model.fit(X_s, y)
    r2  = r2_score(y, model.predict(X_s))
    result.attrs["ridge_r2"]   = round(r2, 3)
    result.attrs["ridge_mape"] = round(
        mean_absolute_percentage_error(item_df["mean_price"], result["ridge_pred"]) * 100, 1
    )
    result.attrs["ridge_feature_names"] = list(extract_features(item_df).columns)
    result.attrs["ridge_coef"]  = model.coef_.tolist()

    return result


# ── Model 2: Qdrant KNN regression ───────────────────────────────────────────

def qdrant_knn_predict(
    item_df: pd.DataFrame,
    client,
    embed_fn,
    collection: str,
    k: int = 15,
) -> pd.DataFrame:
    """
    For each item, retrieve K semantic nearest neighbours from Qdrant
    (excluding the item itself) and return a similarity-score-weighted
    average unit price.

    This uses Qdrant as an ML prediction engine — not just a search index.
    """
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    result = item_df.copy()
    knn_preds = []

    for _, row in item_df.iterrows():
        query_text = (
            f"Electrical cable: {row['description']}. "
            f"Spec code: {row.get('spec_code', '')}. "
            f"Unit: {row.get('unit', '')}. "
            f"Quantity: {row.get('qty', '')}."
        )
        try:
            vec = embed_fn(query_text)

            # Get neighbours; exclude same item_no in Python (simpler than filter)
            hits = client.query_points(
                collection_name=collection,
                query=vec,
                limit=k + 6,          # +6 to account for self-matches
                with_payload=True,
            ).points

            # Filter out self-matches (same item_no)
            neighbours = [
                h for h in hits
                if h.payload.get("item_no") != row["item_no"]
                and h.payload.get("unit_price") is not None
                and h.payload.get("unit_price", 0) > 0
            ][:k]

            if not neighbours:
                knn_preds.append(None)
                continue

            weights = np.array([h.score for h in neighbours])
            prices  = np.array([h.payload["unit_price"] for h in neighbours])
            knn_preds.append(float(np.average(prices, weights=weights)))

        except Exception:
            knn_preds.append(None)

    result["knn_pred"] = knn_preds
    return result


# ── Ensemble ──────────────────────────────────────────────────────────────────

def ensemble_predict(ridge_df: pd.DataFrame) -> pd.DataFrame:
    """
    Blend Ridge + KNN.  Falls back to Ridge-only if KNN not available.
    Adds: ensemble_pred, model_agreement, confidence_flag
    """
    df = ridge_df.copy()
    has_knn = "knn_pred" in df.columns and df["knn_pred"].notna().any()

    if has_knn:
        df["ensemble_pred"] = df[["ridge_pred", "knn_pred"]].mean(axis=1)
        df["model_divergence_pct"] = (
            ((df["ridge_pred"] - df["knn_pred"]).abs() / df["mean_price"] * 100)
            .round(1)
        )
    else:
        df["ensemble_pred"] = df["ridge_pred"]
        df["model_divergence_pct"] = 0.0

    df["ensemble_error_pct"] = (
        (df["ensemble_pred"] - df["mean_price"]) / df["mean_price"] * 100
    ).round(2)

    # Flag uncertain items: ridge and knn diverge > 20% OR error > 30%
    df["confidence_flag"] = (
        (df["model_divergence_pct"] > 20) | (df["ensemble_error_pct"].abs() > 30)
    ).map({True: "Uncertain", False: "Confident"})

    return df


# ── Bidder vs market predictions ──────────────────────────────────────────────

def bidder_vs_market(
    df: pd.DataFrame,
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    """
    For every bidder × item pair, compute deviation from the ensemble prediction.
    Returns a bidder-level summary with risk scores.
    """
    merged = df.merge(
        predictions[["item_no", "ensemble_pred"]],
        on="item_no",
        how="left",
    )
    merged["vs_market_pct"] = (
        (merged["unit_price"] - merged["ensemble_pred"]) / merged["ensemble_pred"] * 100
    ).round(2)

    summary = (
        merged.groupby("bidder")
        .agg(
            n_priced      = ("unit_price", "count"),
            pct_above_10  = ("vs_market_pct", lambda x: (x > 10).mean() * 100),
            pct_below_10  = ("vs_market_pct", lambda x: (x < -10).mean() * 100),
            avg_premium   = ("vs_market_pct", "mean"),
            max_premium   = ("vs_market_pct", "max"),
            min_premium   = ("vs_market_pct", "min"),
        )
        .round(1)
        .reset_index()
    )

    # Risk score: high if consistently above market
    summary["market_risk_score"] = (
        summary["avg_premium"].clip(lower=-50, upper=100) / 100 * 50
        + summary["pct_above_10"] / 100 * 50
    ).clip(lower=0, upper=100).round(1)

    return summary.sort_values("avg_premium")


# ── Convenience: build item_df from raw df ────────────────────────────────────

def build_item_df(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-item mean price from the bid DataFrame."""
    item_df = (
        df.groupby(["item_no", "description", "spec_code", "qty", "unit"])
        ["unit_price"]
        .mean()
        .reset_index()
        .rename(columns={"unit_price": "mean_price"})
        .dropna(subset=["mean_price"])
    )
    return item_df.reset_index(drop=True)
