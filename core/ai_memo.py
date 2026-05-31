"""
AI-powered award recommendation memo generator.
Uses GPT-4o-mini to produce a professional procurement memo from bid analytics.
"""

import datetime
import openai
from core.env import get_env

MODEL = "gpt-4o-mini"


def _get_client() -> openai.OpenAI:
    api_key = get_env("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    return openai.OpenAI(api_key=api_key)


def generate_award_memo(
    project_name: str,
    scorecard_rows: list[dict],
    anomaly_summary: dict,
    scope_gap_summary: dict,
    savings_estimate: float,
    custom_notes: str = "",
) -> str:
    """
    Generate a professional procurement award recommendation memo.

    Args:
        project_name: e.g. "Project Bimbi – LV Cable Supply"
        scorecard_rows: list of dicts from vendor_scorecard(), top 3
        anomaly_summary: {"count": int, "high_count": int, "low_count": int, "max_z": float}
        scope_gap_summary: {"missing_cells": int, "na_cells": int}
        savings_estimate: estimated savings (USD) from pushing anomalous HIGH prices to market
        custom_notes: any additional context the user wants included
    """
    today = datetime.date.today().strftime("%B %d, %Y")

    top = scorecard_rows[0]
    alt = scorecard_rows[1] if len(scorecard_rows) > 1 else None

    bidder_rows = "\n".join(
        f"  - Bidder {r['bidder']}: Total ${r['total_bid']:,.0f} | "
        f"Score {r['overall_score']:.1f}/100 | Rank #{r['rank']}"
        for r in scorecard_rows
    )

    system_prompt = (
        "You are a senior procurement engineer writing a formal internal award "
        "recommendation memo. Tone: professional, concise, factual. "
        "Use numbered sections. No filler phrases. Maximum 500 words."
    )

    user_prompt = f"""
Write a procurement award recommendation memo for the following project.

PROJECT: {project_name}
DATE: {today}

BIDDER SCORECARD (multi-criteria: price 40%, coverage 30%, consistency 30%):
{bidder_rows}

PRICE ANOMALY ANALYSIS:
- {anomaly_summary.get('count', 0)} anomalous line items detected (Z-score > 1.8)
- Overpriced flags: {anomaly_summary.get('high_count', 0)} | Underpriced flags: {anomaly_summary.get('low_count', 0)}
- Highest Z-score deviation: {anomaly_summary.get('max_z', 0):.1f}σ
- Estimated negotiation savings (if anomalous HIGH prices pushed to market mean): ${savings_estimate:,.0f}

SCOPE COMPLETENESS:
- Missing prices: {scope_gap_summary.get('missing_cells', 0)} item-bidder pairs
- Explicit exclusions (N/A): {scope_gap_summary.get('na_cells', 0)} item-bidder pairs

RECOMMENDED AWARD: Bidder {top['bidder']} — ${top['total_bid']:,.0f} — Score {top['overall_score']:.1f}/100
{f"ALTERNATE: Bidder {alt['bidder']} — ${alt['total_bid']:,.0f} — Score {alt['overall_score']:.1f}/100" if alt else ""}

ADDITIONAL CONTEXT FROM EVALUATOR:
{custom_notes if custom_notes.strip() else "None"}

Structure the memo as:
1. Executive Summary
2. Bid Evaluation Summary (table-format in text)
3. Price Anomaly Findings & Negotiation Opportunities
4. Scope Completeness Assessment
5. Award Recommendation & Rationale
6. Conditions / Next Steps

Use USD formatting. Keep each section tight.
"""

    client = _get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=900,
    )
    return response.choices[0].message.content
