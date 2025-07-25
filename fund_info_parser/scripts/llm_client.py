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
You are an SEC‑filing extraction assistant that parses ETF 497‑K filings.

**Return ONE object of strictly valid JSON** – nothing else, no markdown – with exactly these keys and value types:

{
  "fund_name":                str,
  "ticker":                   str | null,                    // upper‑case ticker only
  "underlying_type":          str | null,                    // enum below
  "underlying_asset":         str | null,                    // ticker if available, else full name
  "fund_basis":               str | null,                    // enum below
  "leveraged_etf":            boolean | null,
  "leverage_multiple":        float | null,                  // +2.0, ‑3.0, never a percent
  "rebalancing_timescale":    str | null,                    // enum below
  "inception_date":           str | null,                    // MM/DD/YYYY
  "management_fee":           float | null,                  // 0.75 means 0.75 %
  "expense_fee":              float | null,
  "total_operating_fee":      float | null,
  "net_total_after_waiver":   float | null,
  "investment_objective":     str | null,
  "principal_strategies":     str | null
}

### Assemble the json with the appropriate categories for select variables:
- underlying_type: "index" | "single_stock" | "sector" | "commodity" | "currency" | "crypto" | "bond" | "volatility" | null
- fund_basis: "equities" | "futures" | "options" | "swaps" | "cfds" | null
- rebalancing_timescale: "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | null

### Parsing notes
1. **Ticker**: first upper‑case ticker found; if absent, null.  
2. **Underlying direction**: if filing uses words like “inverse”, “short”, “bear”, or a negative percent, set `leverage_multiple` negative. Remove “%”, divide by 100 if needed.  
3. **underlying_type**: if possible classify as more specific (ie bond, crypto, currency) before more general (ie index, single-stock, sector)
4. **Fees**: strip “%” or “basis points”, convert to float percentage (0.5 % → 0.5).  
5. **Date**: parse any common long form (e.g. “January 3, 2023”) into MM/DD/YYYY.  
6. If a field is genuinely missing, output `null` (without quotes).
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
