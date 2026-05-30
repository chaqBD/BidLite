"""
Procurement analytics computed on top of the bid DataFrame.
All functions return plain DataFrames or dicts — no UI logic here.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


BIDDERS = ["A", "B", "C", "D", "E", "F"]


# ── Price Comparison ──────────────────────────────────────────────────────────

def price_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot: rows = line items, columns = bidders, values = unit_price.
    Adds avg, min, max columns.
    """
    pivot = df.pivot_table(
        index=["item_no", "description", "spec_code", "qty", "unit"],
        columns="bidder",
        values="unit_price",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None

    present = [b for b in BIDDERS if b in pivot.columns]
    pivot["avg_price"] = pivot[present].mean(axis=1)
    pivot["min_price"] = pivot[present].min(axis=1)
    pivot["max_price"] = pivot[present].max(axis=1)
    pivot["spread_pct"] = ((pivot["max_price"] - pivot["min_price"]) / pivot["min_price"] * 100).round(1)
    return pivot


def total_bid_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Total proposal price per bidder with rank."""
    totals = (
        df.groupby("bidder")["total_price"]
        .sum()
        .reset_index()
        .rename(columns={"total_price": "total_bid"})
        .sort_values("total_bid")
    )
    totals["rank"] = range(1, len(totals) + 1)
    min_bid = totals["total_bid"].min()
    totals["premium_vs_low"] = ((totals["total_bid"] - min_bid) / min_bid * 100).round(2)
    return totals


# ── Anomaly Detection ─────────────────────────────────────────────────────────

def detect_price_anomalies(df: pd.DataFrame, z_threshold: float = 1.8) -> pd.DataFrame:
    """
    For each line item, flag bidders whose unit price deviates more than
    z_threshold standard deviations from the item mean.
    Returns rows with anomaly=True only.
    """
    records = []
    for item_no, group in df.groupby("item_no"):
        prices = group["unit_price"].dropna()
        if len(prices) < 3:
            continue
        mean = prices.mean()
        std = prices.std()
        if std == 0:
            continue
        for _, row in group.iterrows():
            if pd.isna(row["unit_price"]):
                continue
            z = abs((row["unit_price"] - mean) / std)
            direction = "HIGH" if row["unit_price"] > mean else "LOW"
            records.append({
                **row.to_dict(),
                "item_mean": round(mean, 4),
                "item_std": round(std, 4),
                "z_score": round(z, 2),
                "anomaly": z > z_threshold,
                "direction": direction if z > z_threshold else "normal",
            })
    result = pd.DataFrame(records)
    if result.empty:
        # Return typed empty DataFrame so callers can safely access column names
        empty_cols = list(df.columns) + ["item_mean", "item_std", "z_score", "anomaly", "direction"]
        return pd.DataFrame(columns=empty_cols)
    return result[result["anomaly"]].reset_index(drop=True)


# ── Scope Gap ─────────────────────────────────────────────────────────────────

def scope_gap_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a matrix (item_no × bidder) with values:
      'Priced'  — unit_price is present
      'Missing' — unit_price is null / zero
      'N/A'     — definition indicates not applicable
    """
    def status(row):
        defn = str(row.get("definition", "")).upper()
        if "N/A" in defn or defn == "NAN":
            return "N/A"
        if pd.isna(row.get("unit_price")) or row.get("unit_price") == 0:
            return "Missing"
        return "Priced"

    df2 = df.copy()
    df2["status"] = df2.apply(status, axis=1)
    pivot = df2.pivot_table(
        index=["item_no", "description"],
        columns="bidder",
        values="status",
        aggfunc="first",
    ).reset_index()
    pivot.columns.name = None
    return pivot


# ── Vendor Scoring ────────────────────────────────────────────────────────────

def vendor_scorecard(df: pd.DataFrame) -> pd.DataFrame:
    """
    Multi-criteria vendor score (0–100, higher = better):
      - Price competitiveness (40%): inverse rank of total bid
      - Coverage completeness (30%): % items priced
      - Price consistency (30%): inverse of coefficient of variation across items
    """
    totals = total_bid_summary(df)
    n_bidders = len(totals)

    # Price rank score: lowest bidder = 100, highest = 0
    totals["price_score"] = (n_bidders - totals["rank"]) / (n_bidders - 1) * 100

    # Coverage
    item_count = df["item_no"].nunique()
    coverage = (
        df[df["unit_price"].notna() & (df["unit_price"] > 0)]
        .groupby("bidder")["item_no"]
        .nunique()
        .reset_index()
        .rename(columns={"item_no": "priced_items"})
    )
    coverage["coverage_score"] = coverage["priced_items"] / item_count * 100

    # Consistency: low CV = high score
    cv = (
        df.groupby("bidder")["unit_price"]
        .agg(lambda x: x.std() / x.mean() if x.mean() > 0 else 1)
        .reset_index()
        .rename(columns={"unit_price": "cv"})
    )
    max_cv = cv["cv"].max() or 1
    cv["consistency_score"] = (1 - cv["cv"] / max_cv) * 100

    scorecard = totals[["bidder", "total_bid", "rank", "price_score", "premium_vs_low"]]
    scorecard = scorecard.merge(coverage[["bidder", "coverage_score"]], on="bidder", how="left")
    scorecard = scorecard.merge(cv[["bidder", "consistency_score"]], on="bidder", how="left")
    scorecard["overall_score"] = (
        scorecard["price_score"] * 0.40
        + scorecard["coverage_score"] * 0.30
        + scorecard["consistency_score"] * 0.30
    ).round(1)

    return scorecard.sort_values("overall_score", ascending=False)


# ── Category Breakdown ────────────────────────────────────────────────────────

def category_spend(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate total spend by spec_code for Pareto chart."""
    cat = (
        df.groupby(["spec_code", "bidder"])["total_price"]
        .sum()
        .reset_index()
    )
    return cat
