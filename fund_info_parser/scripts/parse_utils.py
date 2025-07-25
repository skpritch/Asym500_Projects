"""
pdf_utils.py
------------

Helpers to turn searchable SEC PDF pages into plain text strings.
"""

from pathlib import Path
from typing import List
from bs4 import BeautifulSoup
import pdfplumber

def html_to_text(html_path: Path) -> str:
    """
    Read an .htm/.html file and return its visible text.
    """
    raw = html_path.read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(raw, 'html.parser')
    # get_text() will collapse tags into a single string
    return soup.get_text(separator='\n')

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
