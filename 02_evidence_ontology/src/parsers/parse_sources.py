from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "seed_law_articles.json"
PARSED_PATH = ROOT / "data" / "parsed" / "parsed_segments.json"


PARAGRAPH_PATTERN = re.compile(r"([①②③④⑤⑥⑦⑧⑨⑩])\s*([^①②③④⑤⑥⑦⑧⑨⑩\[]+)")


def parse_law_article(record: dict) -> list[dict]:
    segments: list[dict] = []
    for match in PARAGRAPH_PATTERN.finditer(record["raw_text"]):
        paragraph, text = match.groups()
        segments.append({
            "source_id": record["source_id"],
            "source_type": record["document_type"],
            "source_name": record["document_name"],
            "article": record["article"],
            "paragraph": paragraph,
            "page": None,
            "section": None,
            "original_text": text.strip(),
            "effective_date": record["effective_date"],
            "source_url": record["source_url"],
            "retrieved_at": record["retrieved_at"],
        })
    return segments


def main() -> None:
    records = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    parsed: list[dict] = []
    for record in records:
        if record["document_type"] in {"law", "enforcement_decree"}:
            parsed.extend(parse_law_article(record))
    PARSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    PARSED_PATH.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
