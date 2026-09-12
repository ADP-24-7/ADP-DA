from __future__ import annotations

import json
from pathlib import Path

from scripts.materialize_regulatory_lineage import materialize

ROOT = Path(__file__).resolve().parents[2]


def test_materializes_only_current_non_review_registry_mappings() -> None:
    artifact, registries = materialize()
    review_queue = json.loads(
        (ROOT / "regulatory_baseline" / "REGULATORY_REVIEW_QUEUE.json").read_text(
            encoding="utf-8"
        )
    )
    review_ids = {
        review["regulatory_evidence_id"] for review in review_queue["reviews"]
    }

    assert artifact["automatic_approval"] is False
    assert artifact["automatic_activation"] is False
    assert artifact["target_lifecycle_state"] == "DRAFT"
    assert len(artifact["materializations"]) == 14
    assert not (
        review_ids
        & {
            item["regulatory_evidence_id"]
            for item in artifact["materializations"]
        }
    )
    assert all(item["requirement_refs"] for item in artifact["materializations"])
    assert all(item["control_refs"] for item in artifact["materializations"])
    assert registries["AI"]["summary"]["fully_connected"] == 7
    assert registries["DIGITAL_ASSET"]["summary"]["fully_connected"] == 9


def test_checked_in_materialization_is_reproducible() -> None:
    generated, _ = materialize()
    checked_in = json.loads(
        (
            ROOT
            / "regulatory_baseline"
            / "REGULATORY_LINEAGE_MATERIALIZATION.json"
        ).read_text(encoding="utf-8")
    )

    assert checked_in == generated
