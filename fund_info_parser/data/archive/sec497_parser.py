#!/usr/bin/env python
"""
sec497_parser.py
----------------
Parse one or many Form 497 PDFs into a JSON-Lines file (one dict per line).

Example
-------
python -m src.sec497_parser data/raw/*.pdf \
       --out data/extracted/sec497.jsonl \
       --model o4-mini --workers 4
"""

import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import pandas as pd
from tqdm import tqdm

from fund_info_parser.scripts.parse_utils import pdf_to_pages
from data.archive.fund_splitter import split_into_blocks
from scripts.llm_client import extract_block


def save_jsonl(records: List[dict], out_path: Path) -> None:
    """Append each dict to *out_path* as one JSON object per line."""
    out_path.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def blocks_in_pdf(pdf_path: Path) -> int:
    """Quick utility for sizing the progress bar."""
    pages = pdf_to_pages(pdf_path)
    return len(split_into_blocks(pages))


def process_pdf(pdf_path: Path, model: str, pbar: tqdm) -> List[dict]:
    pages = pdf_to_pages(pdf_path)
    blocks = split_into_blocks(pages)
    records: List[dict] = []

    for block in blocks:
        sha1 = hashlib.sha1(block.encode()).hexdigest()
        try:
            data = extract_block(block, model=model)
            data.update({"source_file": pdf_path.name, "block_sha1": sha1})
            records.append(data)
        except Exception as exc:
            print(f"[WARN] {pdf_path.name} block skipped: {exc}", file=sys.stderr)
        pbar.update(1)
    return records


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Parse SEC 497 PDFs → JSONL")
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/extracted/sec497.jsonl"),
        help="output .jsonl (JSON Lines) file",
    )
    parser.add_argument("--model", default="o4-mini")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    total_blocks = sum(blocks_in_pdf(p) for p in args.pdfs)
    all_records: List[dict] = []

    with tqdm(total=total_blocks, unit="fund") as bar:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            fut_to_pdf = {
                pool.submit(process_pdf, pdf, args.model, bar): pdf for pdf in args.pdfs
            }
            for fut in as_completed(fut_to_pdf):
                all_records.extend(fut.result())

    save_jsonl(all_records, args.out)
    print(f"Wrote {len(all_records)} funds → {args.out}")


if __name__ == "__main__":
    main()
