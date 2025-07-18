"""
pdf_utils.py
------------

Helpers to turn searchable SEC PDF pages into plain text strings.
"""

from pathlib import Path
from typing import List

import pdfplumber


def pdf_to_pages(pdf_path: Path, *, x_tol: float = 2, y_tol: float = 2) -> List[str]:
    """
    Extract text from each page of a text-selectable PDF.

    Parameters
    ----------
    pdf_path : Path
        Path to the .pdf file.
    x_tol, y_tol : float
        Tolerances passed to pdfplumber.extract_text for layout tweaking.

    Returns
    -------
    List[str]
        One string per page (empty string if pdfplumber couldn’t read a page).
    """
    pages: List[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=x_tol, y_tolerance=y_tol) or ""
            pages.append(text)
    return pages
