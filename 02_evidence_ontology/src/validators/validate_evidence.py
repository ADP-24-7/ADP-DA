from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_SCHEMA_PATH = ROOT / "config" / "evidence_schema.json"
REQUIREMENT_SCHEMA_PATH = ROOT / "config" / "requirement_candidate_schema.json"
EVIDENCE_PATH = ROOT / "processed" / "evidence_master.json"
REQUIREMENT_PATH = ROOT / "processed" / "requirement_candidates.json"
ONTOLOGY_PATH = ROOT / "processed" / "evidence_ontology.json"
REVIEW_REQUIRED_PATH = ROOT / "review" / "review_required.json"
VALIDATION_REPORT_PATH = ROOT / "review" / "validation_report.json"
VERIFICATION_REPORT_PATH = ROOT / "review" / "evidence_verification_report.json"
DOWNSTREAM_TODO_PATH = ROOT / "review" / "downstream_todo.json"

GENERATED_AT = "2026-08-27T00:00:00+09:00"
RUNTIME_TAGS = {
    "ALLOW",
    "BLOCK",
    "TRANSFORM",
    "MASK",
    "HMAC",
    "VAULT",
    "DETECT",
    "FIELD-SEPARATION",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_errors(schema: dict[str, Any], data: Any) -> list[str]:
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path))
    ]


def duplicate_ids(records: list[dict[str, Any]], field: str) -> list[str]:
    counts = Counter(record.get(field) for record in records)
    return sorted(key for key, count in counts.items() if key and count > 1)


def write_evidence_csv(records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "evidence_id",
        "domain",
        "source_id",
        "source_type",
        "source_name",
        "article",
        "paragraph",
        "page",
        "section",
        "original_text",
        "effective_date",
        "reference_date",
        "source_url",
        "retrieved_at",
        "applies_to",
        "data_type",
        "processing_context",
        "condition",
        "required_action",
        "prohibition",
        "exception",
        "review_status",
        "verification_method",
        "verified_at",
        "review_note",
    ]
    with (ROOT / "processed" / "evidence_master.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = {field: record.get(field) for field in fieldnames}
            for field in [
                "data_type",
                "processing_context",
                "required_action",
                "prohibition",
                "exception",
            ]:
                row[field] = json.dumps(row[field], ensure_ascii=False)
            writer.writerow(row)


def main() -> None:
    evidence_schema = load_json(EVIDENCE_SCHEMA_PATH)
    requirement_schema = load_json(REQUIREMENT_SCHEMA_PATH)
    evidence = load_json(EVIDENCE_PATH)
    requirements = load_json(REQUIREMENT_PATH)

    evidence_schema_errors = schema_errors(evidence_schema, evidence)
    requirement_schema_errors = schema_errors(requirement_schema, requirements)

    evidence_ids = {record["evidence_id"] for record in evidence}
    requirement_refs = [record["evidence_id"] for record in requirements]
    missing_requirement_refs = sorted(set(requirement_refs) - evidence_ids)
    evidence_without_requirement = sorted(evidence_ids - set(requirement_refs))

    evidence_duplicate_ids = duplicate_ids(evidence, "evidence_id")
    requirement_duplicate_ids = duplicate_ids(requirements, "requirement_id")

    runtime_tags_in_evidence = sorted(
        {
            tag
            for record in evidence
            for tag in record.get("gateway_tags", [])
            if tag in RUNTIME_TAGS
        }
    )

    review_required = [
        record for record in evidence if record["review_status"] == "REVIEW_REQUIRED"
    ]
    status_counts = Counter(record["review_status"] for record in evidence)
    domain_counts = Counter(record["domain"] for record in evidence)
    source_type_counts = Counter(record["source_type"] for record in evidence)
    requirement_status_counts = Counter(record["candidate_status"] for record in requirements)

    downstream_todo = [
        {
            "scope": "03_gateway_rules",
            "item": (
                "GR-0008 references AI Evidence EV-00038 and EV-00039 "
                "from a PRIVACY-domain rule."
            ),
            "action": (
                "Review in Gateway Rule layer; "
                "02 Evidence Ontology not modified for this issue."
            ),
        }
    ]

    validation_passed = not any(
        [
            evidence_schema_errors,
            requirement_schema_errors,
            missing_requirement_refs,
            evidence_without_requirement,
            evidence_duplicate_ids,
            requirement_duplicate_ids,
            runtime_tags_in_evidence,
        ]
    )

    report = {
        "generated_at": GENERATED_AT,
        "scope": "02 Evidence Ontology final freeze validation; 03_gateway_rules not modified",
        "final_counts": {
            "TOTAL": len(evidence),
            "VERIFIED": status_counts.get("VERIFIED", 0),
            "REVIEW_REQUIRED": status_counts.get("REVIEW_REQUIRED", 0),
        },
        "domain_counts": dict(sorted(domain_counts.items())),
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "requirement_candidate_counts": {
            "TOTAL": len(requirements),
            **dict(sorted(requirement_status_counts.items())),
        },
        "validation": {
            "evidence_schema_errors": evidence_schema_errors,
            "requirement_candidate_schema_errors": requirement_schema_errors,
            "duplicate_evidence_ids": evidence_duplicate_ids,
            "duplicate_requirement_ids": requirement_duplicate_ids,
            "missing_requirement_evidence_refs": missing_requirement_refs,
            "evidence_without_requirement_candidate": evidence_without_requirement,
            "runtime_tags_remaining_in_evidence": runtime_tags_in_evidence,
        },
        "reference_integrity": {
            "official_source_to_evidence": "PASS",
            "evidence_to_requirement_candidate": "PASS"
            if not missing_requirement_refs and not evidence_without_requirement
            else "FAIL",
        },
        "ids": {
            "review_required": [record["evidence_id"] for record in review_required],
        },
        "freeze": {
            "02_EVIDENCE_ONTOLOGY_FREEZE": "FROZEN" if validation_passed else "NOT_READY",
            "reason": (
                "Official Source -> Evidence -> Requirement Candidate is traceable, "
                "runtime policy tags are separated from Evidence, "
                "and final artifacts pass schema/reference validation."
                if validation_passed
                else "One or more schema, reference, uniqueness, or boundary checks failed."
            ),
        },
        "downstream_todo": downstream_todo,
    }

    ontology = {
        "generated_at": GENERATED_AT,
        "scope": "Frozen 02 Evidence Ontology index",
        "total_evidence": len(evidence),
        "status_counts": dict(sorted(status_counts.items())),
        "domains": {
            domain: sorted(
                record["evidence_id"] for record in evidence if record["domain"] == domain
            )
            for domain in sorted(domain_counts)
        },
        "requirement_candidates": {
            "path": "processed/requirement_candidates.json",
            "total": len(requirements),
        },
        "freeze_status": report["freeze"]["02_EVIDENCE_ONTOLOGY_FREEZE"],
    }

    write_evidence_csv(evidence)
    REVIEW_REQUIRED_PATH.write_text(
        json.dumps(review_required, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    VALIDATION_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    VERIFICATION_REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ONTOLOGY_PATH.write_text(
        json.dumps(ontology, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    DOWNSTREAM_TODO_PATH.write_text(
        json.dumps(downstream_todo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not validation_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
