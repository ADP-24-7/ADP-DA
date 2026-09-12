from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "regulatory_baseline"
STATUS = {"CURRENT", "REVIEW_REQUIRED", "UNRESOLVED"}
TRACE_STATUS = {"CONNECTED", "PENDING_REVIEW", "MISSING"}
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


def load(name: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((BASELINE / name).read_text(encoding="utf-8")),
    )


def validate() -> None:
    snapshot = load("OFFICIAL_REGULATORY_SNAPSHOT_2026-09-12.json")
    ai = load("AI_REGULATORY_REGISTRY.json")
    digital_asset = load("DIGITAL_ASSET_REGULATORY_REGISTRY.json")
    fixtures = load("REGULATORY_LINEAGE_E2E_FIXTURES.json")
    review_queue = load("REGULATORY_REVIEW_QUEUE.json")
    materialization = load("REGULATORY_LINEAGE_MATERIALIZATION.json")

    sources = {item["source_id"]: item for item in snapshot["sources"]}
    assert len(sources) == len(snapshot["sources"]), "duplicate regulatory source_id"
    assert snapshot["retrieved_at"] == "2026-09-12T00:00:00+09:00"
    for source in sources.values():
        assert source["official_url"].startswith("https://")
        assert source["official_identifier"]
        assert source["applicable_articles"]
        assert source["domain"] in {"AI", "DIGITAL_ASSET", "BOTH"}
        assert SHA256.fullmatch(source["content_digest"])
    evidence_identity: dict[str, tuple[str, str]] = {}
    for registry in (ai, digital_asset):
        for item in registry["entries"]:
            assert item["repository_status"] in STATUS
            assert set(item["trace"].values()) <= TRACE_STATUS
            assert item["source_id"] in sources
            assert (
                item["regulatory_evidence_id"]
                == sources[item["source_id"]]["regulatory_evidence_id"]
            )
            assert item["content_digest"] == sources[item["source_id"]]["content_digest"]
            assert item["source_url"] == sources[item["source_id"]]["official_url"]
            assert item["official_identifier"]
            assert SHA256.fullmatch(item["content_digest"])
            identity = (item["source_id"], item["content_digest"])
            previous = evidence_identity.setdefault(item["regulatory_evidence_id"], identity)
            assert previous == identity, "common source identity differs by domain"
            assert item["linked_requirements"], f"missing requirement mapping: {item['source_id']}"
            assert item["linked_controls"], f"missing control mapping: {item['source_id']}"

    registry_statuses: dict[str, str] = {}
    for registry in (ai, digital_asset):
        for item in registry["entries"]:
            previous_status = registry_statuses.setdefault(
                item["source_id"], item["repository_status"]
            )
            assert previous_status == item["repository_status"], (
                "common source status differs by domain"
            )

    counts = Counter(registry_statuses.values())
    assert sum(counts.values()) == 32
    assert counts == {"CURRENT": 23, "REVIEW_REQUIRED": 9}
    assert review_queue["count"] == 9
    assert review_queue["automatic_approval"] is False
    review_ids = {review["regulatory_evidence_id"] for review in review_queue["reviews"]}
    expected_review_ids = {
        item["regulatory_evidence_id"]
        for registry in (ai, digital_asset)
        for item in registry["entries"]
        if item["repository_status"] == "REVIEW_REQUIRED"
    }
    assert review_ids == expected_review_ids
    required_review_fields = {
        "review_id", "regulatory_evidence_id", "domain", "issue", "official_source",
        "effective_date", "affected_requirement", "affected_control", "affected_policy",
        "recommended_review_action", "status",
    }
    for review in review_queue["reviews"]:
        assert required_review_fields <= review.keys()
        assert review["status"] == "PENDING_REVIEW"
    assert materialization["automatic_approval"] is False
    assert materialization["automatic_activation"] is False
    assert materialization["target_lifecycle_state"] == "DRAFT"
    materialized_keys = {
        (item["domain"], item["regulatory_evidence_id"])
        for item in materialization["materializations"]
    }
    assert len(materialized_keys) == 14
    assert not ({item[1] for item in materialized_keys} & review_ids)
    registry_entries = {
        (registry["domain"], item["regulatory_evidence_id"]): item
        for registry in (ai, digital_asset)
        for item in registry["entries"]
    }
    for item in materialization["materializations"]:
        entry = registry_entries[(item["domain"], item["regulatory_evidence_id"])]
        assert item["source_digest"] == entry["content_digest"]
        assert item["requirement_refs"] == entry["linked_requirements"]
        assert item["control_refs"] == entry["linked_controls"]
        assert set(entry["trace"].values()) == {"CONNECTED"}
        assert item["lifecycle_state"] == "DRAFT"
    assert ai["summary"]["fully_connected"] == 7
    assert digital_asset["summary"]["fully_connected"] == 9
    assert len(fixtures["cases"]) >= 2
    assert {case["domain"] for case in fixtures["cases"]} >= {"AI", "DIGITAL_ASSET"}
    for case in fixtures["cases"]:
        source = sources[case["regulatory_source_id"]]
        assert case["regulatory_evidence_id"] == source["regulatory_evidence_id"]
        assert case["source_digest"] == source["content_digest"]
        assert case["requirement_refs"] and case["control_refs"]


if __name__ == "__main__":
    validate()
    print("Regulatory baseline and lineage validation PASS")
