"""Validate DA handoff contract files."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"

SCHEMA_FILES = [
    CONTRACTS / "evaluation_artifact.schema.json",
    CONTRACTS / "policy_evaluation_artifact.schema.json",
    CONTRACTS / "runtime_data_class_crosswalk.schema.json",
    CONTRACTS / "workload_purpose_binding.schema.json",
]

TAXONOMY_FILES = [
    CONTRACTS / "taxonomies" / "regulatory_data_categories.v1.json",
    CONTRACTS / "taxonomies" / "processing_contexts.v1.json",
]


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return value


def require_keys(path: Path, payload: dict[str, object], keys: set[str]) -> None:
    missing = keys.difference(payload)
    if missing:
        missing_keys = ", ".join(sorted(missing))
        raise ValueError(f"{path} is missing required metadata keys: {missing_keys}")


def validate_schema_file(path: Path) -> None:
    payload = load_json(path)
    require_keys(path, payload, {"$schema", "$id", "title", "type", "properties"})


def validate_taxonomy_file(path: Path) -> None:
    payload = load_json(path)
    require_keys(path, payload, {"schema_version", "taxonomy_name", "$defs"})
    if payload["schema_version"] != "v1":
        raise ValueError(f"{path} must use schema_version v1")


def main() -> None:
    for path in SCHEMA_FILES:
        validate_schema_file(path)
    for path in TAXONOMY_FILES:
        validate_taxonomy_file(path)


if __name__ == "__main__":
    main()
