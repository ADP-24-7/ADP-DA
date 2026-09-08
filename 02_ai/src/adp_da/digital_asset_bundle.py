"""Build and publish the exact Digital Asset Bundle contract consumed by BE P0-5."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from adp_da.storage import (
    ArtifactIntegrityError,
    ArtifactStore,
    build_content_addressed_object_key,
    sha256_digest,
)
from adp_da.storage.core import ArtifactStorageError

SCHEMA_VERSION = "adp-digital-asset-artifact-bundle/v1"
CANONICAL_CONTRACT = {
    "artifact_id": "ADP-DIGITAL-ASSET-RUNTIME-CONTRACT",
    "artifact_version": "1.0.0",
    "content_digest": "sha256:886842702fad124a95e73f0f714ffacef56d5cbd5a4c0f222440279d106b3504",
}
ROLE_FILES = {
    "OUTBOUND_REQUIREMENT_MATRIX": (
        "outbound-requirement-matrix.json",
        "outbound-requirement-matrix-v1.schema.json",
    ),
    "POLICY_EVALUATION": ("policy-evaluation.json", "policy-evaluation-v1.schema.json"),
    "BINDING": ("binding.json", "binding-v1.schema.json"),
    "RUNTIME_DATA_CROSSWALK": (
        "runtime-data-crosswalk.json",
        "runtime-data-crosswalk-v1.schema.json",
    ),
    "RUNTIME_PIPELINE": ("runtime-pipeline.json", "runtime-pipeline-v1.schema.json"),
}
EXPECTED_CONTROLS = {
    "APPROVED_VS_REQUESTED_MATCH",
    "REQUIRED_OUTBOUND_FIELD_PRESENCE",
    "REQUIRED_EXACT_PRESERVATION",
    "TRANSFORM_FIELD_SEPARATION",
    "DESTINATION_SPECIFIC_PAYLOAD",
    "TRACE_BINDING",
}
EXPECTED_DECISIONS = {"PASS", "BLOCK", "REVIEW"}
EXPECTED_PIPELINE = [
    "APPROVED_TRANSACTION_LOAD",
    "ARTIFACT_BINDING",
    "OUTBOUND_GUARD",
    "EXTERNAL_HANDOFF",
    "POST_EXECUTION_REBINDING",
]
ALLOWED_RUNTIME_DATA_CLASSES = {
    "CUSTOMER_IDENTIFIER",
    "ACCOUNT_IDENTIFIER",
    "TRANSACTION_IDENTIFIER",
    "FINANCIAL_AMOUNT",
    "FINANCIAL_METADATA",
    "BUSINESS_METADATA",
}
BLOCKING_GAP = re.compile(r"(^|[^A-Z])(UNMAPPED|TBD|CONTRACT_GAP)([^A-Z]|$)")


@dataclass(frozen=True)
class BuiltDigitalAssetBundle:
    manifest: dict[str, Any]
    manifest_bytes: bytes
    files: dict[str, bytes]


@dataclass(frozen=True)
class PublishedDigitalAssetBundle:
    manifest_reference: str
    expected_content_digest: str
    storage_manifest_digest: str
    created_object_keys: tuple[str, ...]

    def ingest_request(self) -> dict[str, str]:
        return {
            "manifestReference": self.manifest_reference,
            "expectedContentDigest": self.expected_content_digest,
        }


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return sha256_digest(canonical_json_bytes(value))


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError(f"invalid JSON artifact: {path.name}") from error
    if not isinstance(value, dict):
        raise ArtifactIntegrityError(f"JSON artifact must be an object: {path.name}")
    return value


def _validate(schema: dict[str, Any], value: dict[str, Any], label: str) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.path)
    )
    if errors:
        raise ArtifactIntegrityError(f"{label} does not match BE P0-5 schema: {errors[0].message}")


def _payload(documents: dict[str, dict[str, Any]], role: str) -> dict[str, Any]:
    document = documents.get(role)
    payload = document.get("payload") if document else None
    if not isinstance(payload, dict):
        raise ArtifactIntegrityError(f"Digital Asset role payload is missing: {role}")
    return payload


def _reject_blocking_gap(value: Any) -> None:
    if isinstance(value, str) and BLOCKING_GAP.search(value.upper()):
        raise ArtifactIntegrityError("Digital Asset Bundle contains a blocking contract gap")
    if isinstance(value, dict):
        for item in value.values():
            _reject_blocking_gap(item)
    elif isinstance(value, list):
        for item in value:
            _reject_blocking_gap(item)


def _exact_string_set(value: Any, expected: set[str], label: str) -> None:
    if (
        not isinstance(value, list)
        or any(not isinstance(item, str) for item in value)
        or len(value) != len(expected)
        or set(value) != expected
    ):
        raise ArtifactIntegrityError(f"Digital Asset semantic mismatch: {label}")


def validate_bundle_semantics(
    manifest: dict[str, Any], documents: dict[str, dict[str, Any]]
) -> None:
    """Mirror the cross-document checks enforced by the BE P0-5 semantic validator."""
    for document in documents.values():
        _reject_blocking_gap(document)

    manifest_binding = manifest.get("binding")
    if not isinstance(manifest_binding, dict):
        raise ArtifactIntegrityError("Digital Asset manifest binding is missing")
    artifact_binding = _payload(documents, "BINDING")
    binding_fields = (
        "execution_pack",
        "workload_id",
        "purpose_code",
        "destination_profile_id",
    )
    if any(manifest_binding.get(field) != artifact_binding.get(field) for field in binding_fields):
        raise ArtifactIntegrityError("Digital Asset manifest and BINDING artifact do not match")

    crosswalk = _payload(documents, "RUNTIME_DATA_CROSSWALK").get("runtime_data_classes")
    if (
        not isinstance(crosswalk, list)
        or not crosswalk
        or any(not isinstance(item, str) for item in crosswalk)
        or not ALLOWED_RUNTIME_DATA_CLASSES.issuperset(crosswalk)
    ):
        raise ArtifactIntegrityError("Digital Asset runtime data crosswalk contains a gap")

    policy = _payload(documents, "POLICY_EVALUATION")
    _exact_string_set(policy.get("decision_semantics"), EXPECTED_DECISIONS, "decision set")
    if policy.get("external_action_on_unresolved") != "DENY":
        raise ArtifactIntegrityError("Digital Asset unresolved external action must be DENY")

    controls = _payload(documents, "OUTBOUND_REQUIREMENT_MATRIX").get("controls")
    _exact_string_set(controls, EXPECTED_CONTROLS, "outbound control set")

    pipeline = _payload(documents, "RUNTIME_PIPELINE").get("stages")
    if pipeline != EXPECTED_PIPELINE:
        raise ArtifactIntegrityError("Digital Asset runtime pipeline order does not match BE")


def build_digital_asset_bundle(
    *,
    source_dir: Path,
    schema_dir: Path,
    artifact_id: str,
    artifact_version: str,
    institution_id: str,
    destination_profile_id: str,
) -> BuiltDigitalAssetBundle:
    files: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, str]] = []
    for role, (filename, schema_filename) in ROLE_FILES.items():
        document = _read_json(source_dir / filename)
        schema = _read_json(schema_dir / schema_filename)
        _validate(schema, document, role)
        content = canonical_json_bytes(document)
        digest = sha256_digest(content)
        reference = build_content_addressed_object_key(
            "handoff/validated", artifact_id, artifact_version, f"{role.lower()}.json", digest
        )
        files[reference] = content
        documents[role] = document
        entries.append(
            {
                "role": role,
                "reference": reference,
                "digest": digest,
                "schema_reference": f"contracts/digital-asset-artifacts/{schema_filename}",
                "schema_digest": canonical_digest(schema),
            }
        )
    without_digest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "artifact_version": artifact_version,
        "canonical_contract": CANONICAL_CONTRACT,
        "binding": {
            "institution_id": institution_id,
            "execution_pack": "DIGITAL_ASSET",
            "workload_id": "tokenized_asset_purchase",
            "purpose_code": "DIGITAL_ASSET_PURCHASE",
            "destination_profile_id": destination_profile_id,
        },
        "blocking_gaps": [],
        "files": entries,
    }
    manifest = {**without_digest, "content_digest": canonical_digest(without_digest)}
    manifest_schema = _read_json(schema_dir / "digital-asset-artifact-bundle-v1.schema.json")
    _validate(manifest_schema, manifest, "Digital Asset Bundle Manifest")
    validate_bundle_semantics(manifest, documents)
    return BuiltDigitalAssetBundle(manifest, canonical_json_bytes(manifest), files)


def publish_digital_asset_bundle(
    store: ArtifactStore, bundle: BuiltDigitalAssetBundle
) -> PublishedDigitalAssetBundle:
    created: list[str] = []
    artifact_id = str(bundle.manifest["artifact_id"])
    artifact_version = str(bundle.manifest["artifact_version"])
    manifest_storage_digest = sha256_digest(bundle.manifest_bytes)
    manifest_key = build_content_addressed_object_key(
        "handoff/validated",
        artifact_id,
        artifact_version,
        "manifest.json",
        manifest_storage_digest,
    )
    try:
        for reference, content in bundle.files.items():
            digest = sha256_digest(content)
            if store.put(reference, content, digest=digest, content_type="application/json"):
                created.append(reference)
            store.get(reference, expected_digest=digest)
        if store.put(
            manifest_key,
            bundle.manifest_bytes,
            digest=manifest_storage_digest,
            content_type="application/json",
        ):
            created.append(manifest_key)
        store.get(manifest_key, expected_digest=manifest_storage_digest, max_bytes=1_048_576)
    except Exception:
        for key in reversed(created):
            try:
                store.delete(key)
            except ArtifactStorageError:
                pass
        raise
    return PublishedDigitalAssetBundle(
        manifest_reference=manifest_key,
        expected_content_digest=str(bundle.manifest["content_digest"]),
        storage_manifest_digest=manifest_storage_digest,
        created_object_keys=tuple(created),
    )


def verify_published_digital_asset_bundle(
    store: ArtifactStore,
    *,
    manifest_reference: str,
    expected_content_digest: str,
    storage_manifest_digest: str,
    schema_dir: Path,
) -> dict[str, Any]:
    """Download and validate the same manifest/files contract consumed by BE P0-5."""
    manifest_bytes = store.get(
        manifest_reference,
        expected_digest=storage_manifest_digest,
        max_bytes=1_048_576,
    )
    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactIntegrityError("Digital Asset Bundle Manifest is invalid JSON") from error
    if not isinstance(manifest, dict):
        raise ArtifactIntegrityError("Digital Asset Bundle Manifest must be an object")
    manifest_schema = _read_json(schema_dir / "digital-asset-artifact-bundle-v1.schema.json")
    _validate(manifest_schema, manifest, "Digital Asset Bundle Manifest")
    without_digest = {key: value for key, value in manifest.items() if key != "content_digest"}
    actual_content_digest = canonical_digest(without_digest)
    if (
        manifest["content_digest"] != actual_content_digest
        or expected_content_digest != actual_content_digest
    ):
        raise ArtifactIntegrityError("Digital Asset Bundle content digest mismatch")

    verified_roles: list[str] = []
    documents: dict[str, dict[str, Any]] = {}
    references: set[str] = set()
    for entry in manifest["files"]:
        role = str(entry["role"])
        reference = str(entry["reference"])
        if role not in ROLE_FILES or role in documents or reference in references:
            raise ArtifactIntegrityError(f"unsupported Digital Asset role: {role}")
        references.add(reference)
        _, schema_filename = ROLE_FILES[role]
        schema = _read_json(schema_dir / schema_filename)
        if canonical_digest(schema) != entry["schema_digest"]:
            raise ArtifactIntegrityError(f"Digital Asset schema digest mismatch: {role}")
        content = store.get(reference, expected_digest=str(entry["digest"]))
        try:
            document = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ArtifactIntegrityError(f"Digital Asset file is invalid JSON: {role}") from error
        if not isinstance(document, dict):
            raise ArtifactIntegrityError(f"Digital Asset file must be an object: {role}")
        _validate(schema, document, role)
        documents[role] = document
        verified_roles.append(role)
    if set(verified_roles) != set(ROLE_FILES):
        raise ArtifactIntegrityError("Digital Asset Bundle roles are incomplete")
    validate_bundle_semantics(manifest, documents)
    return {
        "run_type": "NCP_DIGITAL_ASSET_BUNDLE_VERIFY",
        "status": "PASS",
        "bucket": store.bucket,
        "manifestReference": manifest_reference,
        "expectedContentDigest": expected_content_digest,
        "storageManifestDigest": storage_manifest_digest,
        "verifiedRoles": verified_roles,
        "downloadDigestMatch": True,
        "credentialValuesRecorded": False,
    }
