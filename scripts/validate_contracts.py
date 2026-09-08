"""Validate DA handoff contract files."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "02_ai" / "contracts"
DIGITAL_ASSET_LOADER_CONTRACTS = ROOT / "03_digital_asset" / "contracts" / "be_loader_v1"

SCHEMA_FILES = [
    CONTRACTS / "artifact_storage_manifest.schema.json",
    CONTRACTS / "ai-evaluation-bundle.schema.json",
    CONTRACTS / "ai_runtime_contract_vnext.schema.json",
    CONTRACTS / "ai_runtime_validation_vnext.schema.json",
    CONTRACTS / "evaluation_artifact.schema.json",
    CONTRACTS / "policy_evaluation_artifact.schema.json",
    CONTRACTS / "runtime_data_class_crosswalk.schema.json",
    CONTRACTS / "workload_purpose_binding.schema.json",
]

BE_LOADER_SCHEMA_FILES = [
    DIGITAL_ASSET_LOADER_CONTRACTS / "digital-asset-artifact-bundle-v1.schema.json",
    DIGITAL_ASSET_LOADER_CONTRACTS / "outbound-requirement-matrix-v1.schema.json",
    DIGITAL_ASSET_LOADER_CONTRACTS / "policy-evaluation-v1.schema.json",
    DIGITAL_ASSET_LOADER_CONTRACTS / "binding-v1.schema.json",
    DIGITAL_ASSET_LOADER_CONTRACTS / "runtime-data-crosswalk-v1.schema.json",
    DIGITAL_ASSET_LOADER_CONTRACTS / "runtime-pipeline-v1.schema.json",
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
    Draft202012Validator.check_schema(payload)


def validate_be_loader_schema_file(path: Path) -> None:
    """Validate frozen BE schemas without imposing DA-only metadata conventions."""
    payload = load_json(path)
    require_keys(path, payload, {"$schema", "type", "properties"})
    Draft202012Validator.check_schema(payload)


def validate_taxonomy_file(path: Path) -> None:
    payload = load_json(path)
    require_keys(path, payload, {"schema_version", "taxonomy_name", "$defs"})
    if payload["schema_version"] != "v1":
        raise ValueError(f"{path} must use schema_version v1")


def main() -> None:
    for path in SCHEMA_FILES:
        validate_schema_file(path)
    for path in BE_LOADER_SCHEMA_FILES:
        validate_be_loader_schema_file(path)
    for path in TAXONOMY_FILES:
        validate_taxonomy_file(path)


if __name__ == "__main__":
    main()
