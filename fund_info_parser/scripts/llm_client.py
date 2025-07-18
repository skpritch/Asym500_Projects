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
You are a SEC-filing extraction assistant examining ETF 497k filings.
In assembling the following json perform the following classification:

{ "underlying_theme": "index" | "single-stock" | "sector" | "commodity" | "currency" | "bond" | null
  "primary_basis": "equities/stocks" | "options" | "swaps" | null
}
Return ONLY valid JSON with these keys:

{
  "fund_name": str,
  "ticker": str | null,
  "underlying_theme": str | null
  "primary_basis": str | null
  "benchmark_underlying": str | null,
  "leverage_percent": str | null,
  "rebalancing_timescale": str | null
  "inception_date": str | null,
  "management_fee": str | null,
  "expense_fee": str | null,
  "total_operating_fee": str | null,
  "net_total_after_waiver": str | null,
  "distribution_frequency": str | null,
  "tax_status": str | null,
  "investment_objective": str | null,
  "principal_strategies": str | null,
}

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
