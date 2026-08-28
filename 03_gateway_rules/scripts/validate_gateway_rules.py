from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[0]

CONTROL_SCHEMA = ROOT / "schemas" / "control_schema.json"
TEST_SCHEMA = ROOT / "schemas" / "test_schema.json"
POLICY_SCHEMA = ROOT / "schemas" / "policy_candidate_schema.json"
CONTROLS = ROOT / "processed" / "controls.json"
TESTS = ROOT / "processed" / "tests.json"
POLICIES = ROOT / "processed" / "policy_candidates.json"
TRACEABILITY = ROOT / "processed" / "traceability.json"
REQUIREMENT_CLASSIFICATION = ROOT / "processed" / "requirement_classification.json"
MIGRATION = ROOT / "migration" / "legacy_rule_mapping.json"
LEGACY_RULES = ROOT / "rules" / "gateway_rules.json"
REQUIREMENTS = PROJECT_ROOT / "02_evidence_ontology" / "processed" / "requirement_candidates.json"
EVIDENCE = PROJECT_ROOT / "02_evidence_ontology" / "processed" / "evidence_master.json"
VALIDATION_REPORT = ROOT / "review" / "validation_report.json"
ORPHAN_REPORT = ROOT / "review" / "orphan_report.json"

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

FINAL_TRANSFORMS = {
    "MASK",
    "HMAC",
    "HMAC-PSEUDO",
    "VAULT",
    "VAULT-TOKEN",
    "GENERALIZE",
    "FIELD-SEPARATION",
    "REMOVE",
    "KEEP",
}

RUNTIME_CONTROL_TYPES = {
    "AUTHORIZATION",
    "PURPOSE_LIMITATION",
    "DATA_ACCESS",
    "DATA_MINIMIZATION",
    "FIELD_ALLOWLIST",
    "SENSITIVE_DETECTION",
    "EGRESS_CONTROL",
    "TRANSFORM",
    "VAULT_MAPPING",
    "ENCRYPTION",
    "NETWORK_CONTROL",
    "DIGITAL_ASSET_FIELD_SEPARATION",
}


def load(path: Path) -> Any:
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


def main() -> None:
    controls = load(CONTROLS)
    tests = load(TESTS)
    policies = load(POLICIES)
    load(TRACEABILITY)
    requirement_classification = load(REQUIREMENT_CLASSIFICATION)
    migration = load(MIGRATION)
    rules = load(LEGACY_RULES)
    requirements = load(REQUIREMENTS)
    evidence = load(EVIDENCE)

    control_ids = {record["control_id"] for record in controls}
    test_ids = {record["test_id"] for record in tests}
    requirement_ids = {record["requirement_id"] for record in requirements}
    review_required_requirement_ids = {
        record["requirement_id"]
        for record in requirements
        if record["candidate_status"] == "REVIEW_REQUIRED"
    }
    legacy_rule_ids = {record["rule_id"] for record in rules}

    dangling_requirement_ids = sorted(
        {
            requirement_id
            for record in controls + policies
            for requirement_id in record.get("requirement_ids", [])
            if requirement_id not in requirement_ids
        }
    )
    dangling_control_ids = sorted(
        {
            control_id
            for record in tests + policies
            for control_id in record.get("control_ids", [])
            if control_id not in control_ids
        }
    )
    dangling_test_ids = sorted(
        {
            test_id
            for record in policies
            for test_id in record.get("test_ids", [])
            if test_id not in test_ids
        }
    )
    orphan_requirements = sorted(
        requirement_ids
        - {requirement_id for record in controls for requirement_id in record["requirement_ids"]}
    )
    controls_without_tests = sorted(
        control_ids - {control_id for record in tests for control_id in record["control_ids"]}
    )
    runtime_controls = {
        record["control_id"]
        for record in controls
        if record["control_type"] in RUNTIME_CONTROL_TYPES
    }
    controls_without_policy = sorted(
        runtime_controls
        - {control_id for record in policies for control_id in record["control_ids"]}
    )
    governance_controls_without_policy = sorted(
        control_ids
        - runtime_controls
        - {control_id for record in policies for control_id in record["control_ids"]}
    )
    missing_legacy_migrations = sorted(
        legacy_rule_ids - {record["legacy_rule_id"] for record in migration}
    )

    direct_runtime_in_evidence = sorted(
        {
            tag
            for record in evidence
            for tag in record.get("gateway_tags", [])
            if tag in RUNTIME_TAGS
        }
    )
    gateway_tags_remaining = sorted(
        {tag for record in evidence for tag in record.get("gateway_tags", [])}
    )

    promoted_review_required_policies = sorted(
        record["policy_candidate_id"]
        for record in policies
        if any(req_id in review_required_requirement_ids for req_id in record["requirement_ids"])
        and record.get("promotion_blocked") is not True
    )

    final_transform_without_artifact = sorted(
        record["policy_candidate_id"]
        for record in policies
        if (
            record["candidate_transform"] in FINAL_TRANSFORMS
            or any(
                option in FINAL_TRANSFORMS
                for option in record.get("candidate_transform_options", [])
            )
        )
        and "data_evaluation_artifact" not in record["validation_dependencies"]
    )

    threshold_without_artifact = sorted(
        record["policy_candidate_id"]
        for record in policies
        if "threshold" in json.dumps(record, ensure_ascii=False).lower()
        and "data_evaluation_artifact" not in record["validation_dependencies"]
    )

    direct_evidence_runtime_refs = sorted(
        record["policy_candidate_id"]
        for record in policies
        if "evidence_ids" in record or "evidence_refs" in record
    )

    active_policy_candidates = sorted(
        record["policy_candidate_id"]
        for record in policies
        if record.get("status") == "ACTIVE" or record.get("policy_maturity") == "ACTIVE"
    )

    active_policy_chain_missing = sorted(
        record["policy_candidate_id"]
        for record in policies
        if record["status"] in {"PROJECT_PROVISIONAL", "VALIDATION_REQUIRED"}
        and (not record["requirement_ids"] or not record["control_ids"] or not record["test_ids"])
    )

    gr_0008_role = next(
        (record for record in migration if record["legacy_rule_id"] == "GR-0008"), {}
    )

    legacy_rule_names = {record["rule_name"] for record in rules}
    controls_using_legacy_names = sorted(
        record["control_id"] for record in controls if record["control_name"] in legacy_rule_names
    )
    control_test_1_to_1_ratio = len(controls) == len(tests) and all(
        len([test for test in tests if record["control_id"] in test["control_ids"]]) == 1
        for record in controls
    )
    duplicate_expected_behavior = {
        text: count
        for text, count in Counter(record["expected_behavior"] for record in tests).items()
        if count > 1
    }
    duplicate_failure_condition = {
        text: count
        for text, count in Counter(record["failure_condition"] for record in tests).items()
        if count > 1
    }
    duplicate_required_artifact = {
        text: count
        for text, count in Counter(record["required_artifact"] for record in tests).items()
        if count > 1
    }
    legacy_action_by_rule = {record["rule_id"]: record["decision"]["action"] for record in rules}
    candidate_action_legacy_copy_rate = {
        "copied": sum(
            1
            for policy in policies
            if len(policy["reason_codes"]) == 2
            and policy["reason_codes"][0] in legacy_action_by_rule
            and policy["candidate_action"] == legacy_action_by_rule[policy["reason_codes"][0]]
        ),
        "total": len(policies),
    }
    all_requirements_with_runtime_policy = sorted(
        record["requirement_id"]
        for record in requirement_classification
        if record["governance_only"]
        and any(record["requirement_id"] in policy["requirement_ids"] for policy in policies)
    )

    report = {
        "generated_at": "2026-08-27T00:00:00+09:00",
        "scope": "03 Gateway Rules migration validation against frozen 02 Requirement Candidates",
        "counts": {
            "legacy_rules": len(rules),
            "controls": len(controls),
            "tests": len(tests),
            "policy_candidates": len(policies),
            "requirement_classification": dict(
                sorted(
                    Counter(
                        record["requirement_class"] for record in requirement_classification
                    ).items()
                )
            ),
            "migration_audit_classification": dict(
                sorted(Counter(record["audit_classification"] for record in migration).items())
            ),
            "project_provisional_policies": sum(
                1 for record in policies if record["policy_maturity"] == "PROJECT_PROVISIONAL"
            ),
            "validation_required_policies": sum(
                1 for record in policies if record["policy_maturity"] == "VALIDATION_REQUIRED"
            ),
            "promotion_blocked_policies": sum(
                1 for record in policies if record.get("promotion_blocked") is True
            ),
            "review_required_affected_policies": sum(
                1 for record in policies if record["evidence_maturity"] == "REVIEW_REQUIRED"
            ),
            "active_policy_candidates": len(active_policy_candidates),
        },
        "validation": {
            "control_schema_errors": schema_errors(load(CONTROL_SCHEMA), controls),
            "test_schema_errors": schema_errors(load(TEST_SCHEMA), tests),
            "policy_candidate_schema_errors": schema_errors(load(POLICY_SCHEMA), policies),
            "duplicate_control_ids": duplicate_ids(controls, "control_id"),
            "duplicate_test_ids": duplicate_ids(tests, "test_id"),
            "duplicate_policy_candidate_ids": duplicate_ids(policies, "policy_candidate_id"),
            "dangling_requirement_ids": dangling_requirement_ids,
            "dangling_control_ids": dangling_control_ids,
            "dangling_test_ids": dangling_test_ids,
            "orphan_requirements": orphan_requirements,
            "controls_without_tests": controls_without_tests,
            "runtime_controls_without_policy": controls_without_policy,
            "direct_runtime_decision_in_evidence": direct_runtime_in_evidence,
            "gateway_tags_remaining_in_evidence": gateway_tags_remaining,
            "direct_evidence_runtime_reference_in_policy_candidates": direct_evidence_runtime_refs,
            "review_required_policy_promotion_errors": promoted_review_required_policies,
            "final_transform_without_artifact": final_transform_without_artifact,
            "threshold_without_artifact": threshold_without_artifact,
            "active_policy_candidates": active_policy_candidates,
            "active_policy_chain_missing": active_policy_chain_missing,
            "missing_legacy_rule_migrations": missing_legacy_migrations,
            "gr_0008_migration_status_error": []
            if gr_0008_role.get("migration_role") == "PROVENANCE_ONLY"
            and gr_0008_role.get("audit_classification") == "REQUIRES_REDESIGN"
            else [f"GR-0008 role is {gr_0008_role}"],
        },
        "semantic_warnings": {
            "controls_using_legacy_rule_names": controls_using_legacy_names,
            "control_test_1_to_1_ratio": control_test_1_to_1_ratio,
            "duplicate_expected_behavior": duplicate_expected_behavior,
            "duplicate_failure_condition": duplicate_failure_condition,
            "duplicate_required_artifact": duplicate_required_artifact,
            "governance_controls_without_policy": governance_controls_without_policy,
            "governance_only_requirements_with_policy": all_requirements_with_runtime_policy,
            "candidate_action_legacy_copy_rate": candidate_action_legacy_copy_rate,
        },
    }

    validation_passed = not any(report["validation"].values())
    report["result"] = "PASS" if validation_passed else "FAIL"

    orphan_report = {
        "generated_at": report["generated_at"],
        "orphan_requirements": orphan_requirements,
        "controls_without_tests": controls_without_tests,
        "runtime_controls_without_policy": controls_without_policy,
        "governance_controls_without_policy": governance_controls_without_policy,
        "dangling_requirement_ids": dangling_requirement_ids,
        "dangling_control_ids": dangling_control_ids,
        "dangling_test_ids": dangling_test_ids,
    }

    VALIDATION_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    ORPHAN_REPORT.write_text(
        json.dumps(orphan_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if not validation_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
