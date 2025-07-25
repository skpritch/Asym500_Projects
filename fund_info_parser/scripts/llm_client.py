"""
llm_client.py
-------------

Thin convenience wrapper around the OpenAI Chat Completions API
with retry/backoff & JSON-mode response parsing.
"""

import json
from typing import Dict

import backoff
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, RateLimitError

load_dotenv()              # picks up OPENAI_API_KEY, etc.

client = OpenAI()

SYSTEM_PROMPT = """
You are a SEC-filing extraction assistant examining ETF 497k filings. Return ONLY valid JSON with these keys:

{
  "fund_name": str,
  "ticker": str | null,
  "underlying_type": str | null,
  "underlying_asset": str | null,
  "fund_basis": str | null
  "leveraged_etf": boolean | null,
  "leverage_multiple": float | null,
  "rebalancing_timescale": str | null
  "inception_date": str | null,
  "management_fee": float | null,
  "expense_fee": float | null,
  "total_operating_fee": float | null,
  "net_total_after_waiver": float | null,
  "investment_objective": str | null,
  "principal_strategies": str | null,
}

In assembling the json report with the following categorization or format:
- "underlying_type": "index" | "single-stock" | "sector" | "commodity" | "currency" | "bond" | null
- "underlying_asset": report solely a ticker
- "fund_basis": how are the returns actually generated?: "equities/stocks" | "options" | "swaps" | null
- "leveraged_etf": product that returns a multiple of percent changes in an underlying stock (no capping of upside or downside movement)
- "leverage_multiple": return some multiple rather than a percent (ie 2.0 instead of 200%). Positive for bull / long, negative for bear / short
- "rebalancing_timescale": "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | null
- "inception_date": report as MM/DD/YYYY
- "management_fee", "expense_fee", "total_operating_fee", "net_total_after_waiver": report as a percentage (ie 0.5 for 0.5%, 0.0 for 0.00%)

If a field is not present, set it to null.
"""


@backoff.on_exception(
    backoff.expo,
    (RateLimitError, APIConnectionError),
    max_time=120,
)
def extract_block(
    block_text: str,
    *,
    model: str = "o4-mini",
) -> Dict:
    """
    Send one fund block to the LLM and return the parsed JSON dict.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            # The word “json” is REQUIRED when using response_format=json_object.
            "content": f"Extract the fund data as json.\n---\n{block_text}\n---",
        },
    ]

    resp = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=messages,
    )
    return json.loads(resp.choices[0].message.content)
