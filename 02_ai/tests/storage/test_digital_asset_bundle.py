from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest
from adp_da.digital_asset_bundle import (
    ALLOWED_RUNTIME_DATA_CLASSES,
    EXPECTED_CONTROLS,
    EXPECTED_DECISIONS,
    EXPECTED_PIPELINE,
    BuiltDigitalAssetBundle,
    build_digital_asset_bundle,
    canonical_digest,
    publish_digital_asset_bundle,
    validate_bundle_semantics,
    verify_published_digital_asset_bundle,
)
from adp_da.storage import ArtifactIntegrityError, LocalArtifactStore

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "03_digital_asset" / "artifacts" / "be_loader_v1"
SCHEMAS = ROOT / "03_digital_asset" / "contracts" / "be_loader_v1"
SCHEMA_RAW_DIGESTS = {
    "digital-asset-artifact-bundle-v1.schema.json": (
        "89d5e9efcf4d3e7961473c56be889848762632a5ecd3bbfdee8d023cd6c4aac8"
    ),
    "binding-v1.schema.json": ("95b302b6c32237592b206b3f2705b0fba5c12f3fa3e8dc809f2d4504ee176365"),
    "outbound-requirement-matrix-v1.schema.json": (
        "81b433829161fdfd5359726025a4cbd5a53f681aa9e2676280cbec468a5425a5"
    ),
    "policy-evaluation-v1.schema.json": (
        "e47ffa9e6c486f4343c0d4f26b4a82c7d42520199cf1a07bd64e45eff0d1b002"
    ),
    "runtime-data-crosswalk-v1.schema.json": (
        "27ee9cf189d9fc721aa7d5f5f80091d46f620b59860fea0285f54d9abefd980a"
    ),
    "runtime-pipeline-v1.schema.json": (
        "9d7ab3bf9660cfad60f380b2250fa5c8770558b136d2736ef28d357db6e8fae4"
    ),
}


def build_bundle() -> BuiltDigitalAssetBundle:
    return build_digital_asset_bundle(
        source_dir=SOURCE,
        schema_dir=SCHEMAS,
        artifact_id="DA-DIGITAL-ASSET-RUNTIME-CANDIDATE-001",
        artifact_version="1.0.0",
        institution_id="institution_local",
        destination_profile_id="dest_mock_asset_platform_v1",
    )


def test_be_p0_5_schemas_are_exactly_frozen() -> None:
    for filename, expected in SCHEMA_RAW_DIGESTS.items():
        assert hashlib.sha256((SCHEMAS / filename).read_bytes()).hexdigest() == expected


def test_semantic_constants_match_frozen_be_schemas() -> None:
    def schema(filename: str) -> dict[str, object]:
        return json.loads((SCHEMAS / filename).read_text())

    control_items = schema("outbound-requirement-matrix-v1.schema.json")["properties"]["payload"][
        "properties"
    ]["controls"]["items"]["enum"]
    policy = schema("policy-evaluation-v1.schema.json")["properties"]["payload"]["properties"]
    crosswalk_items = schema("runtime-data-crosswalk-v1.schema.json")["properties"]["payload"][
        "properties"
    ]["runtime_data_classes"]["items"]["enum"]
    pipeline_items = schema("runtime-pipeline-v1.schema.json")["properties"]["payload"][
        "properties"
    ]["stages"]["prefixItems"]

    assert set(control_items) == EXPECTED_CONTROLS
    assert set(policy["decision_semantics"]["items"]["enum"]) == EXPECTED_DECISIONS
    assert policy["external_action_on_unresolved"]["const"] == "DENY"
    assert set(crosswalk_items) - {"UNKNOWN"} == ALLOWED_RUNTIME_DATA_CLASSES
    assert [item["const"] for item in pipeline_items] == EXPECTED_PIPELINE


def test_builds_exact_be_p0_5_manifest_contract() -> None:
    bundle = build_bundle()
    manifest = bundle.manifest
    without_digest = {key: value for key, value in manifest.items() if key != "content_digest"}

    assert manifest["schema_version"] == "adp-digital-asset-artifact-bundle/v1"
    assert manifest["content_digest"] == canonical_digest(without_digest)
    assert {entry["role"] for entry in manifest["files"]} == {
        "OUTBOUND_REQUIREMENT_MATRIX",
        "POLICY_EVALUATION",
        "BINDING",
        "RUNTIME_DATA_CROSSWALK",
        "RUNTIME_PIPELINE",
    }
    assert all(entry["reference"].startswith("handoff/validated/") for entry in manifest["files"])
    assert all(
        entry["digest"].removeprefix("sha256:") in entry["reference"] for entry in manifest["files"]
    )
    expected_schema_digests = {
        entry["role"]: entry["schema_digest"]
        for entry in json.loads((SOURCE / "manifest.json").read_text())["files"]
    }
    assert {
        entry["role"]: entry["schema_digest"] for entry in manifest["files"]
    } == expected_schema_digests


def test_local_and_ncp_port_semantics_support_idempotent_bundle_publish(tmp_path: Path) -> None:
    bundle = build_bundle()
    store = LocalArtifactStore(tmp_path, bucket="adp-qa-data-artifacts")

    first = publish_digital_asset_bundle(store, bundle)
    replay = publish_digital_asset_bundle(store, bundle)

    assert len(first.created_object_keys) == 6
    assert replay.created_object_keys == ()
    assert first.ingest_request() == {
        "manifestReference": first.manifest_reference,
        "expectedContentDigest": bundle.manifest["content_digest"],
    }
    assert first.storage_manifest_digest.removeprefix("sha256:") in first.manifest_reference
    verified = verify_published_digital_asset_bundle(
        store,
        manifest_reference=first.manifest_reference,
        expected_content_digest=first.expected_content_digest,
        storage_manifest_digest=first.storage_manifest_digest,
        schema_dir=SCHEMAS,
    )
    assert verified["status"] == "PASS"
    assert verified["run_type"] == "NCP_DIGITAL_ASSET_BUNDLE_VERIFY"
    assert verified["bucket"] == "adp-qa-data-artifacts"
    assert verified["credentialValuesRecorded"] is False
    assert verified["semanticValidation"] == "PASS"
    assert verified["contentAddressedManifest"] is True
    assert set(verified["verifiedRoles"]) == set(
        entry["role"] for entry in bundle.manifest["files"]
    )


def test_bundle_publish_content_addresses_same_identity_with_different_bytes(
    tmp_path: Path,
) -> None:
    first = build_bundle()
    store = LocalArtifactStore(tmp_path, bucket="adp-qa-data-artifacts")
    first_published = publish_digital_asset_bundle(store, first)
    changed_source = tmp_path / "changed-source"
    shutil.copytree(SOURCE, changed_source)
    changed_policy = json.loads((changed_source / "policy-evaluation.json").read_text())
    changed_policy["artifact_id"] = "DA-P0-5-POLICY-EVAL-002"
    (changed_source / "policy-evaluation.json").write_text(json.dumps(changed_policy))
    changed = build_digital_asset_bundle(
        source_dir=changed_source,
        schema_dir=SCHEMAS,
        artifact_id="DA-DIGITAL-ASSET-RUNTIME-CANDIDATE-001",
        artifact_version="1.0.0",
        institution_id="institution_local",
        destination_profile_id="dest_mock_asset_platform_v1",
    )
    changed_published = publish_digital_asset_bundle(store, changed)

    assert first_published.manifest_reference != changed_published.manifest_reference
    assert first_published.expected_content_digest != changed_published.expected_content_digest
    assert len(changed_published.created_object_keys) == 2
    assert (
        verify_published_digital_asset_bundle(
            store,
            manifest_reference=first_published.manifest_reference,
            expected_content_digest=first_published.expected_content_digest,
            storage_manifest_digest=first_published.storage_manifest_digest,
            schema_dir=SCHEMAS,
        )["status"]
        == "PASS"
    )


def test_rejects_manifest_binding_mismatch_before_publish(tmp_path: Path) -> None:
    changed_source = tmp_path / "binding-mismatch"
    shutil.copytree(SOURCE, changed_source)

    with pytest.raises(ArtifactIntegrityError, match="BINDING artifact"):
        build_digital_asset_bundle(
            source_dir=changed_source,
            schema_dir=SCHEMAS,
            artifact_id="DA-DIGITAL-ASSET-RUNTIME-CANDIDATE-001",
            artifact_version="1.0.0",
            institution_id="institution_local",
            destination_profile_id="dest-other",
        )


def test_semantics_reject_unknown_crosswalk_and_pipeline_order() -> None:
    bundle = build_bundle()
    documents_by_role = {
        entry["role"]: json.loads(bundle.files[entry["reference"]])
        for entry in bundle.manifest["files"]
    }
    documents_by_role["RUNTIME_DATA_CROSSWALK"]["payload"]["runtime_data_classes"].append("UNKNOWN")
    with pytest.raises(ArtifactIntegrityError, match="crosswalk"):
        validate_bundle_semantics(bundle.manifest, documents_by_role)

    documents_by_role = {
        entry["role"]: json.loads(bundle.files[entry["reference"]])
        for entry in bundle.manifest["files"]
    }
    documents_by_role["RUNTIME_PIPELINE"]["payload"]["stages"].reverse()
    with pytest.raises(ArtifactIntegrityError, match="pipeline order"):
        validate_bundle_semantics(bundle.manifest, documents_by_role)
