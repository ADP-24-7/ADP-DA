from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEWED_PATH = ROOT / "data" / "reviewed" / "evidence_candidates.json"
OUTPUT_JSON = ROOT / "output" / "evidence.json"
OUTPUT_CSV = ROOT / "output" / "evidence.csv"


REQUIRED_FIELDS = [
    "original_text",
    "source_url",
    "source_name",
    "retrieved_at",
    "review_status",
]


CSV_FIELDS = [
    "evidence_id",
    "source_id",
    "source_type",
    "source_name",
    "article",
    "paragraph",
    "page",
    "section",
    "original_text",
    "applies_to",
    "data_type",
    "condition",
    "required_action",
    "prohibition",
    "exception",
    "effective_date",
    "source_url",
    "retrieved_at",
    "review_status",
    "validation_errors",
]


def validate(record: dict) -> dict:
    errors = [field for field in REQUIRED_FIELDS if not record.get(field)]
    if not (record.get("article") or record.get("page")):
        errors.append("article_or_page")
    if not record.get("original_text"):
        record["review_status"] = "INVALID"
    elif errors and record.get("review_status") != "INVALID":
        record["review_status"] = "REVIEW_REQUIRED"
    record["validation_errors"] = errors
    return record


def main() -> None:
    records = json.loads(REVIEWED_PATH.read_text(encoding="utf-8"))
    validated = [validate(record) for record in records]
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(validated, ensure_ascii=False, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in validated:
            row = {field: record.get(field) for field in CSV_FIELDS}
            row["validation_errors"] = ";".join(record.get("validation_errors", []))
            writer.writerow(row)


if __name__ == "__main__":
    main()
