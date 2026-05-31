"""
GPT-powered interpretation of BidLite's ML price predictions.
The model gives numbers; GPT gives procurement wisdom.
"""

import openai
from core.env import get_env

MODEL = "gpt-4o-mini"


def _client() -> openai.OpenAI:
    key = get_env("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set")
    return openai.OpenAI(api_key=key)


def generate_prediction_insight(
    project_name: str,
    ridge_r2: float,
    ridge_mape: float,
    n_items: int,
    has_knn: bool,
    uncertain_items: list[dict],      # [{description, mean_price, ensemble_pred, divergence_pct}]
    bidder_summary: list[dict],        # [{bidder, avg_premium, pct_above_10, market_risk_score}]
    top_overprice: list[dict],         # [{description, bidder, unit_price, ensemble_pred, vs_market_pct}]
    top_savings: float,                # total USD saving if all above-market priced at prediction
    custom_notes: str = "",
) -> str:
    """
    Generate a GPT commentary that interprets the ML prediction results
    as a senior procurement analyst would.
    """
    uncertain_block = "\n".join(
        f"  • {r['description'][:55]}: predicted ${r['ensemble_pred']:.4f}, "
        f"actual mean ${r['mean_price']:.4f}, "
        f"model divergence {r.get('model_divergence_pct', 0):.1f}%"
        for r in uncertain_items[:5]
    ) or "  None — all predictions are confident."

    bidder_block = "\n".join(
        f"  • Bidder {r['bidder']}: avg {r['avg_premium']:+.1f}% vs market, "
        f"{r['pct_above_10']:.0f}% of items >10% above, "
        f"risk score {r['market_risk_score']:.0f}/100"
        for r in sorted(bidder_summary, key=lambda x: -x["market_risk_score"])
    )

    overprice_block = "\n".join(
        f"  • {r['description'][:45]}: Bidder {r['bidder']} "
        f"at ${r['unit_price']:.4f} vs predicted ${r['ensemble_pred']:.4f} "
        f"({r['vs_market_pct']:+.1f}%)"
        for r in top_overprice[:5]
    ) or "  None detected."

    knn_note = (
        "Both a Ridge regression AND a Qdrant vector-similarity KNN model were used "
        "and blended into an ensemble. Items where these two models diverge significantly "
        "are flagged as uncertain."
        if has_knn else
        "Ridge regression model only (Qdrant KNN unavailable — index not yet built)."
    )

    system = (
        "You are a senior procurement analyst with 15 years of experience in "
        "capital project bid evaluation. You interpret ML price predictions and "
        "translate them into clear, actionable procurement intelligence. "
        "Be direct, specific, and quantitative. Maximum 500 words. "
        "No filler phrases. Use numbered sections."
    )

    user = f"""
Interpret these ML price-prediction results for a procurement bid evaluation.

PROJECT: {project_name}
LINE ITEMS: {n_items}
MODELLING APPROACH: {knn_note}

MODEL ACCURACY (Leave-One-Out cross-validation):
  - R² score: {ridge_r2:.2f}  (1.0 = perfect, 0 = baseline)
  - MAPE: {ridge_mape:.1f}%   (mean absolute % prediction error)

BIDDER SYSTEMATIC DEVIATIONS FROM PREDICTED MARKET PRICE:
{bidder_block}

ITEMS WITH UNCERTAIN PREDICTIONS (models disagree or large error):
{uncertain_block}

MOST SIGNIFICANT ABOVE-MARKET PRICES:
{overprice_block}

ESTIMATED NEGOTIATION SAVING (if above-market items brought to prediction):
  ${top_savings:,.0f} USD

EVALUATOR NOTES: {custom_notes if custom_notes.strip() else "None"}

Write a procurement intelligence commentary with these sections:
1. Model Quality Assessment — is the R² and MAPE good enough to trust the predictions?
2. Market Pricing Dynamics — what do the predictions reveal about this cable market?
3. Bidder Pricing Intelligence — which bidders are aligned/misaligned and what does it imply?
4. High-Uncertainty Items — which items need market clarification before award?
5. Negotiation Recommendations — specific actions, ranked by savings potential
"""

    resp = _client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.25,
        max_tokens=800,
    )
    return resp.choices[0].message.content
