from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "regulatory_baseline"
OUTPUT = BASELINE / "REGULATORY_LINEAGE_MATERIALIZATION.json"
REGISTRIES = {
    "AI": BASELINE / "AI_REGULATORY_REGISTRY.json",
    "DIGITAL_ASSET": BASELINE / "DIGITAL_ASSET_REGULATORY_REGISTRY.json",
}
POLICIES = {
    "AI": {
        "artifact_id": "AI-REGULATORY-EVIDENCE-MATERIALIZATION-2026-09-13",
        "artifact_version": "1.0.0",
        "execution_pack": "AI",
        "workload_id": "customer_summary",
        "purpose_code": "CUSTOMER_SUPPORT",
        "lifecycle_state": "DRAFT",
    },
    "DIGITAL_ASSET": {
        "artifact_id": "DA-REGULATORY-EVIDENCE-MATERIALIZATION-2026-09-13",
        "artifact_version": "1.0.0",
        "execution_pack": "DIGITAL_ASSET",
        "workload_id": "tokenized_asset_purchase",
        "purpose_code": "DIGITAL_ASSET_PURCHASE",
        "lifecycle_state": "DRAFT",
    },
}
EXPECTED_MISSING = {"AI": 11, "DIGITAL_ASSET": 10}
EXPECTED_MATERIALIZED = {"AI": 6, "DIGITAL_ASSET": 8}
MISSING_INVENTORY = {
    "AI": (
        "REF-REG-PIPA-DECREE-2026-09-11",
        "REF-REG-FIN-GOV-ACT-2026",
        "REF-REG-FIN-GOV-DECREE-2026",
        "REF-REG-CREDIT-DECREE-2026-08-13",
        "REF-REG-EFTA-ACT-2026-09-12",
        "REF-REG-EFTA-DECREE-2026-04-28",
        "REF-REG-PIPC-PSEUDONYM-GUIDE-2026",
        "REF-REG-PIPC-PRIVACY-POLICY-GUIDE-2026-04",
        "REF-REG-FSC-MYDATA-SERVICE-GUIDE-2021-07",
        "REF-REG-FSC-FINANCIAL-PRIVACY-GUIDE-2017",
        "REF-REG-FSEC-CRYPTO-GUIDE-2019",
    ),
    "DIGITAL_ASSET": (
        "REF-REG-PIPA-2026-09-11",
        "REF-REG-PIPA-DECREE-2026-09-11",
        "REF-REG-FIN-GOV-ACT-2026",
        "REF-REG-FIN-GOV-DECREE-2026",
        "REF-REG-EFTA-ACT-2026-09-12",
        "REF-REG-EFTA-DECREE-2026-04-28",
        "REF-REG-VA-SUPERVISION-2024-37",
        "REF-REG-FIU-REPORT-SUPERVISION-2026-2",
        "REF-REG-FIU-AML-CFT-2025-2",
        "REF-REG-FATF-VA-TARGETED-UPDATE-2026",
    ),
}


def load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def dump(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def is_missing(entry: dict[str, Any]) -> bool:
    return "MISSING" in entry["trace"].values()


def materialize() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    review_queue = load(BASELINE / "REGULATORY_REVIEW_QUEUE.json")
    review_ids = {
        review["regulatory_evidence_id"] for review in review_queue["reviews"]
    }
    registries = {domain: load(path) for domain, path in REGISTRIES.items()}
    records: list[dict[str, Any]] = []
    deferred: list[dict[str, str]] = []
    counts: dict[str, dict[str, int]] = {}

    for domain, registry in registries.items():
        entries_by_id = {
            entry["regulatory_evidence_id"]: entry for entry in registry["entries"]
        }
        missing = [entries_by_id[evidence_id] for evidence_id in MISSING_INVENTORY[domain]]
        if len(missing) != EXPECTED_MISSING[domain]:
            raise ValueError(
                f"{domain} missing inventory drift: {len(missing)} "
                f"!= {EXPECTED_MISSING[domain]}"
            )
        materialized = 0
        for entry in missing:
            evidence_id = entry["regulatory_evidence_id"]
            if evidence_id in review_ids:
                if not is_missing(entry):
                    raise ValueError(f"review-required mapping was modified: {evidence_id}")
                deferred.append(
                    {
                        "domain": domain,
                        "regulatory_evidence_id": evidence_id,
                        "reason": "REVIEW_REQUIRED_UNCHANGED",
                    }
                )
                continue
            if entry["repository_status"] != "CURRENT":
                raise ValueError(f"non-current evidence cannot materialize: {evidence_id}")
            if not entry["linked_requirements"] or not entry["linked_controls"]:
                raise ValueError(f"explicit Registry mapping is incomplete: {evidence_id}")

            policy = POLICIES[domain]
            records.append(
                {
                    "domain": domain,
                    "source_id": entry["source_id"],
                    "regulatory_evidence_id": evidence_id,
                    "source_version": entry["effective_date"] or registry["as_of"],
                    "source_digest": entry["content_digest"],
                    "law_name": entry["law_name"],
                    "authority": entry["authority"],
                    "official_source": entry["official_source"],
                    "source_url": entry["source_url"],
                    "applicable_articles": entry["applicable_articles"],
                    "effective_date": entry["effective_date"],
                    "requirement_refs": entry["linked_requirements"],
                    "control_refs": entry["linked_controls"],
                    "policy_artifact_id": policy["artifact_id"],
                    "policy_version": policy["artifact_version"],
                    "lifecycle_state": policy["lifecycle_state"],
                    "execution_pack": policy["execution_pack"],
                    "workload_id": policy["workload_id"],
                    "purpose_code": policy["purpose_code"],
                    "review_status": "CONNECTED",
                }
            )
            artifact_ref = f'{policy["artifact_id"]}/{policy["artifact_version"]}'
            if artifact_ref not in entry["linked_policy_artifacts"]:
                entry["linked_policy_artifacts"].append(artifact_ref)
            entry["trace"] = {stage: "CONNECTED" for stage in entry["trace"]}
            materialized += 1

        if materialized != EXPECTED_MATERIALIZED[domain]:
            raise ValueError(
                f"{domain} materialization drift: {materialized} "
                f"!= {EXPECTED_MATERIALIZED[domain]}"
            )
        connected = sum(
            all(state == "CONNECTED" for state in entry["trace"].values())
            for entry in registry["entries"]
        )
        registry["summary"]["fully_connected"] = connected
        registry["summary"]["partial_or_missing"] = len(registry["entries"]) - connected
        counts[domain] = {
            "missing_reviewed": len(missing),
            "materialized": materialized,
            "deferred": len(missing) - materialized,
            "connected_after": connected,
        }

    output = {
        "schema_version": "adp-regulatory-lineage-materialization/v1",
        "as_of": "2026-09-13",
        "source_registry_version": "2026-09-12",
        "automatic_approval": False,
        "automatic_activation": False,
        "target_lifecycle_state": "DRAFT",
        "policy_artifacts": list(POLICIES.values()),
        "counts": counts,
        "materializations": records,
        "deferred": deferred,
    }
    return output, registries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    output, registries = materialize()
    if args.write:
        dump(OUTPUT, output)
        for domain, registry in registries.items():
            dump(REGISTRIES[domain], registry)
    else:
        if not OUTPUT.exists() or load(OUTPUT) != output:
            raise ValueError("materialization artifact is stale; run with --write")
    print(
        "Regulatory lineage materialization PASS: "
        f"{len(output['materializations'])} connected, "
        f"{len(output['deferred'])} review-required mappings unchanged"
    )


if __name__ == "__main__":
    main()
