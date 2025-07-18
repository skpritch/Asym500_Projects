"""
fund_splitter.py
----------------

Splits an entire 497 filing into per-fund text blocks.

The default rule looks for headings similar to:

    GRANITESHARES 2x LONG META ETF — Summary
    ABC Capital XYZ Fund  —  Summary

Adjust `FUND_SPLIT_RE` if an issuer’s style differs.
"""

import re
from typing import List

# A permissive pattern that matches CAPITALIZED headings ending with “– Summary”
FUND_SPLIT_RE = re.compile(
    r"\n("                         # start of a new line
    r"[A-Z][A-Z0-9 /&\-.]{4,}?"    # fund name prefix
    r"[–\-]\s?"                    # accept EN-dash or hyphen
    r"(?:ETF|FUND|TRUST).*?"       # vehicle type
    r"[–\-]\s?SUMMARY"             # trailing “… – Summary”
    r")",
    flags=re.I | re.S              # case-insensitive + DOTALL
)


def split_into_blocks(pages: List[str]) -> List[str]:
    """
    Group the filing into fund-level chunks (heading + body).

    Parameters
    ----------
    pages : List[str]
        List returned by pdf_utils.pdf_to_pages().

    Returns
    -------
    List[str]
        Each element is the concatenated text for one fund.
    """
    whole = "\n".join(pages)
    parts = FUND_SPLIT_RE.split(whole)
    # parts[0] = boilerplate preamble; odd indexes are headings
    blocks = [
        parts[i] + "\n" + parts[i + 1] for i in range(1, len(parts) - 1, 2)
    ]
    return blocks
