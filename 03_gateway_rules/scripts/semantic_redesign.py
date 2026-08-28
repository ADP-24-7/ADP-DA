from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parents[0]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


requirements = load(
    PROJECT_ROOT / "02_evidence_ontology" / "processed" / "requirement_candidates.json"
)
evidence = load(PROJECT_ROOT / "02_evidence_ontology" / "processed" / "evidence_master.json")
legacy_rules = load(ROOT / "rules" / "gateway_rules.json")

req_by_id = {record["requirement_id"]: record for record in requirements}
ev_by_id = {record["evidence_id"]: record for record in evidence}
legacy_by_id = {record["rule_id"]: record for record in legacy_rules}
ev_to_req = {record["evidence_id"]: record["requirement_id"] for record in requirements}

req_to_legacy = defaultdict(list)
for rule in legacy_rules:
    for evidence_id in rule.get("evidence_refs", []):
        if evidence_id in ev_to_req:
            req_to_legacy[ev_to_req[evidence_id]].append(rule["rule_id"])

review_required_evidence = {
    record["evidence_id"] for record in evidence if record.get("review_status") == "REVIEW_REQUIRED"
}
review_required_requirements = {
    record["requirement_id"]
    for record in requirements
    if record.get("candidate_status") == "REVIEW_REQUIRED"
}

classification = {
    "RUNTIME_ENFORCEABLE": [
        "RC-00002",
        "RC-00006",
        "RC-00009",
        "RC-00015",
        "RC-00019",
        "RC-00021",
        "RC-00022",
        "RC-00024",
        "RC-00027",
        "RC-00032",
        "RC-00033",
        "RC-00034",
        "RC-00037",
        "RC-00040",
        "RC-00041",
        "RC-00042",
        "RC-00045",
        "RC-00047",
        "RC-00048",
        "RC-00057",
        "RC-00058",
        "RC-00059",
    ],
    "GOVERNANCE_CONTROL": [
        "RC-00005",
        "RC-00007",
        "RC-00008",
        "RC-00011",
        "RC-00012",
        "RC-00014",
        "RC-00017",
        "RC-00018",
        "RC-00020",
        "RC-00021",
        "RC-00022",
        "RC-00024",
        "RC-00026",
        "RC-00028",
        "RC-00029",
        "RC-00030",
        "RC-00031",
        "RC-00038",
        "RC-00039",
        "RC-00043",
        "RC-00045",
        "RC-00046",
        "RC-00047",
        "RC-00049",
        "RC-00050",
        "RC-00051",
        "RC-00052",
        "RC-00059",
    ],
    "EVALUATION_DEPENDENT": [
        "RC-00001",
        "RC-00003",
        "RC-00004",
        "RC-00010",
        "RC-00040",
        "RC-00044",
    ],
    "NON_RUNTIME_REFERENCE": [
        "RC-00013",
        "RC-00016",
        "RC-00023",
        "RC-00025",
        "RC-00035",
        "RC-00036",
        "RC-00053",
        "RC-00054",
        "RC-00055",
        "RC-00056",
    ],
}

primary_class = {}
for group, requirement_ids in classification.items():
    for requirement_id in requirement_ids:
        primary_class.setdefault(requirement_id, group)
for requirement in requirements:
    primary_class.setdefault(requirement["requirement_id"], "GOVERNANCE_CONTROL")

requirement_analysis = []
for requirement in requirements:
    requirement_id = requirement["requirement_id"]
    source = requirement.get("source_derived_requirement", {})
    evidence_id = requirement["evidence_id"]
    requirement_analysis.append(
        {
            "requirement_id": requirement_id,
            "requirement_meaning": source.get("condition")
            or "; ".join(source.get("required_action", []) + source.get("prohibition", []))
            or "Source-derived requirement candidate requires review.",
            "domain": requirement["domain"],
            "actor": requirement.get("applicability", {}).get("actor", ""),
            "data_scope": requirement.get("applicability", {}).get("data", []),
            "processing_phase": requirement.get("applicability", {}).get("processing_context", []),
            "obligation": source.get("required_action", []),
            "prohibition": source.get("prohibition", []),
            "condition": source.get("condition", ""),
            "requirement_class": primary_class[requirement_id],
            "runtime_enforceable": requirement_id in classification["RUNTIME_ENFORCEABLE"],
            "governance_only": requirement_id in classification["GOVERNANCE_CONTROL"]
            and requirement_id not in classification["RUNTIME_ENFORCEABLE"],
            "evaluation_required": requirement_id in classification["EVALUATION_DEPENDENT"],
            "related_legacy_gr": sorted(req_to_legacy.get(requirement_id, [])),
            "evidence_id": evidence_id,
            "evidence_maturity": ev_by_id[evidence_id].get(
                "review_status", requirement.get("candidate_status")
            ),
            "classification_basis": (
                "Classified from domain, interpretation_tags, processing_context, "
                "candidate_status, and source-derived condition; legacy GR grouping was "
                "not used as the grouping source."
            ),
        }
    )


controls_spec = [
    (
        "CTRL-RUNTIME-001",
        ["RC-00002", "RC-00015", "RC-00019"],
        "EGRESS_CONTROL",
        "Outbound disclosure purpose and recipient gate",
        (
            "Prevent outbound disclosure or transfer when purpose, recipient, or included "
            "identifying information is outside the allowed requirement scope."
        ),
        ["outbound_gateway", "third_party_transfer_gateway"],
        ["pseudonymized_data_processing", "third_party_or_outsourcing"],
        "Project runtime guard; does not define the legal transfer basis.",
        (
            "request fixture, recipient/purpose policy snapshot, final outbound payload, "
            "decision evidence packet"
        ),
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-RUNTIME-002",
        ["RC-00009"],
        "PURPOSE_LIMITATION",
        "Re-identification purpose guard",
        (
            "Detect and block or route attempts whose declared or inferred purpose is "
            "re-identification."
        ),
        ["purpose_classifier", "request_gateway"],
        ["pseudonymized_data_processing"],
        "Project runtime guard; detection logic requires validation before active use.",
        "purpose classifier eval, adversarial prompts, decision trace",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-RUNTIME-003",
        ["RC-00006"],
        "VAULT_MAPPING",
        "Pseudonym mapping separation control",
        (
            "Keep mapping information logically separated from data use flows and prevent "
            "outbound exposure of mapping material."
        ),
        ["vault_boundary", "outbound_gateway"],
        ["pseudonymized_data_processing"],
        "Project technical design candidate; exact vault mechanism is not selected here.",
        "vault access log, mapping egress fixture, policy snapshot",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-EVAL-001",
        ["RC-00001", "RC-00003", "RC-00004", "RC-00010", "RC-00044"],
        "TRANSFORM",
        "Pseudonymization suitability evaluation",
        (
            "Require evaluation before choosing any concrete pseudonymization or "
            "de-identification transform for eligible data."
        ),
        ["evaluation_pipeline"],
        ["pseudonymized_data_processing", "saas_cloud_use"],
        "Evaluation layer owns final transform choice; this control only defines evaluation need.",
        "privacy risk report, utility report, transform option comparison",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-GOV-001",
        ["RC-00005", "RC-00007", "RC-00008"],
        "AUDIT",
        "Pseudonymized data governance record control",
        (
            "Maintain review, logging, and governance evidence for pseudonymized data "
            "processing and transfer governance."
        ),
        ["governance_workflow", "audit_log"],
        ["pseudonymized_data_processing", "third_party_or_outsourcing"],
        "Governance control; not a runtime allow/block decision.",
        "review record, audit trace, governance checklist",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-GOV-002",
        ["RC-00011", "RC-00012"],
        "HUMAN_REVIEW",
        "Credit information consent request handling",
        (
            "Route credit information consent withdrawal and marketing contact cases to "
            "human or workflow review."
        ),
        ["case_management"],
        ["consent_withdrawal", "marketing_contact"],
        "Governance workflow; runtime enforcement can only follow a validated operational policy.",
        "case record, consent state snapshot",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-GOV-003",
        ["RC-00014", "RC-00017", "RC-00018", "RC-00020"],
        "PROVIDER_CONTROL",
        "Outsourcing provider governance control",
        (
            "Check outsourcing contract, supervision, disclosure, and provider obligations "
            "before processing."
        ),
        ["vendor_review", "contract_review"],
        ["third_party_or_outsourcing"],
        "Governance and provider control; not an automatic runtime decision by itself.",
        "contract checklist, provider assessment, supervision log",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-RUNTIME-004",
        ["RC-00021", "RC-00022", "RC-00024", "RC-00041"],
        "EGRESS_CONTROL",
        "Cross-border transfer review and egress gate",
        (
            "Gate cross-border flows on transfer basis, notice, and destination applicability "
            "requirements."
        ),
        ["outbound_gateway", "transfer_review"],
        ["cross_border_transfer", "third_party_or_outsourcing", "ai_use", "saas_cloud_use"],
        "Candidate runtime gate plus governance dependency; legal basis is not invented here.",
        "destination fixture, notice artifact, transfer basis record, outbound payload",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-REF-001",
        ["RC-00013", "RC-00016", "RC-00023"],
        "HUMAN_REVIEW",
        "General legal reference routing",
        (
            "Preserve general legal references as review routing context without making a "
            "runtime policy."
        ),
        ["review_queue"],
        ["compliance_review"],
        "Non-runtime reference; used for human review context only.",
        "review packet showing cited Evidence",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-REF-002",
        ["RC-00025"],
        "AUDIT",
        "Unverified electronic finance reference backlog",
        (
            "Keep REVIEW_REQUIRED electronic finance reference out of promotion until source "
            "details are verified."
        ),
        ["evidence_backlog"],
        [],
        "Backlog tracking only; no runtime control.",
        "source verification result",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-GOV-004",
        ["RC-00026", "RC-00030", "RC-00031", "RC-00049"],
        "MONITORING",
        "Information system monitoring governance",
        (
            "Maintain monitoring and governance evidence for information processing and "
            "security systems."
        ),
        ["monitoring_console", "governance_workflow"],
        ["security_control"],
        "Governance monitoring; does not select a runtime action.",
        "monitoring policy, audit log, review record",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-RUNTIME-005",
        ["RC-00027", "RC-00045", "RC-00047"],
        "AUTHORIZATION",
        "Privileged and administrator account access control",
        (
            "Restrict privileged or administrator account use and require account-control "
            "evidence before promotion."
        ),
        ["identity_gateway", "admin_console"],
        ["security_control", "saas_cloud_use"],
        "Runtime authorization candidate; REVIEW_REQUIRED dependencies block promotion.",
        "account inventory, access policy, negative access fixture, audit trace",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-RUNTIME-006",
        ["RC-00032"],
        "NETWORK_CONTROL",
        "Internal business system network boundary control",
        "Prevent unsupported external network connection patterns for internal business systems.",
        ["network_gateway"],
        ["network_separation", "saas_cloud_use"],
        "Network control candidate; active blocking requires validation artifact.",
        "network path fixture, policy snapshot, connection decision log",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-RUNTIME-007",
        ["RC-00033", "RC-00034", "RC-00048"],
        "ENCRYPTION",
        "Credential and regulated-data protection control",
        (
            "Require protection checks for credentials, electronic-finance data, and SaaS "
            "security handling without choosing a specific encryption implementation."
        ),
        ["secret_scanner", "data_protection_gateway"],
        ["security_control", "saas_cloud_use"],
        "Project technical control; exact cryptographic implementation is outside this artifact.",
        "secret fixture, scan report, protected payload evidence",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-REF-003",
        ["RC-00035", "RC-00036"],
        "HUMAN_REVIEW",
        "AI scope reference control",
        (
            "Use AI definition and scope references for review context without producing "
            "runtime policy."
        ),
        ["review_queue"],
        ["ai_use"],
        "Non-runtime AI reference only.",
        "AI scope review packet",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-GOV-005",
        ["RC-00037", "RC-00038", "RC-00039"],
        "MONITORING",
        "AI usage security governance control",
        (
            "Require governance review, logging, and monitoring for AI usage involving "
            "important or sensitive data."
        ),
        ["ai_governance_workflow", "monitoring_console"],
        ["ai_use", "security_control", "third_party_or_outsourcing"],
        "Governance control; runtime prompt/payload controls require separate policy candidates.",
        "AI usage register, monitoring log, review checklist",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-RUNTIME-008",
        ["RC-00040"],
        "SENSITIVE_DETECTION",
        "AI input sensitive-data detection control",
        "Detect sensitive or credit/personal information in AI input before external AI use.",
        ["ai_input_gateway", "sensitive_data_detector"],
        ["ai_use"],
        "Detection candidate; transform or blocking action remains validation-dependent.",
        "labeled input fixture, detector report, decision trace",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-RUNTIME-009",
        ["RC-00042"],
        "PROVIDER_CONTROL",
        "External AI reuse restriction control",
        (
            "Check provider terms or contract controls for model-improvement reuse before "
            "external AI routing."
        ),
        ["provider_policy_gateway", "ai_input_gateway"],
        ["ai_use"],
        "Runtime/provider gate candidate; legal and contract review remains dependency.",
        "provider terms snapshot, request fixture, routing decision trace",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-GOV-006",
        ["RC-00028", "RC-00029", "RC-00043", "RC-00046"],
        "PROVIDER_CONTROL",
        "SaaS and cloud provider assurance control",
        (
            "Route SaaS/cloud provider eligibility and security assurance requirements "
            "through governance review."
        ),
        ["vendor_review", "cloud_review"],
        ["saas_cloud_use", "security_control"],
        (
            "Governance control; REVIEW_REQUIRED requirements block promotion of dependent "
            "runtime controls."
        ),
        "provider assessment, cloud security checklist, source verification result",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-GOV-007",
        ["RC-00050", "RC-00051", "RC-00052"],
        "HUMAN_REVIEW",
        "Digital asset safeguarding review control",
        "Preserve digital asset safeguarding requirements as compliance review controls.",
        ["digital_asset_review"],
        ["digital_asset_activity", "asset_segregation"],
        "Governance control; not a field-level runtime policy.",
        "safeguarding review packet",
        "PROJECT_PROVISIONAL",
    ),
    (
        "CTRL-REF-004",
        ["RC-00053", "RC-00054", "RC-00055", "RC-00056"],
        "HUMAN_REVIEW",
        "Digital asset definition and transfer backlog control",
        (
            "Keep REVIEW_REQUIRED digital asset definition and transfer references in "
            "backlog until verified."
        ),
        ["evidence_backlog", "digital_asset_review"],
        ["digital_asset_activity", "transaction_data"],
        "Backlog and reference control only.",
        "source verification result",
        "VALIDATION_REQUIRED",
    ),
    (
        "CTRL-RUNTIME-010",
        ["RC-00057", "RC-00058", "RC-00059"],
        "DIGITAL_ASSET_FIELD_SEPARATION",
        "Digital asset wallet and CDD field separation control",
        (
            "Separate wallet, transaction, and customer due-diligence fields for routing "
            "and review without deciding a final transform."
        ),
        ["digital_asset_gateway", "field_classifier"],
        [
            "digital_asset_activity",
            "transaction_data",
            "wallet_address",
            "customer_due_diligence",
        ],
        (
            "Runtime field classification candidate; REVIEW_REQUIRED wallet requirement "
            "blocks promotion."
        ),
        "wallet/CDD fixture, field classification report, audit trace",
        "VALIDATION_REQUIRED",
    ),
]

controls = []
for (
    control_id,
    req_ids,
    control_type,
    name,
    objective,
    enforcement,
    phases,
    boundary,
    validation,
    maturity,
) in controls_spec:
    controls.append(
        {
            "control_id": control_id,
            "requirement_ids": req_ids,
            "control_type": control_type,
            "control_name": name,
            "objective": objective,
            "enforcement_point": enforcement,
            "processing_phase": phases,
            "implementation_boundary": boundary,
            "validation_requirement": validation,
            "provenance": {
                "source": "02_evidence_ontology/processed/requirement_candidates.json",
                "legacy_rule_ids": sorted(
                    {rule for req_id in req_ids for rule in req_to_legacy.get(req_id, [])}
                ),
                "note": (
                    "Designed from Requirement Candidate meaning; legacy GR is provenance "
                    "only."
                ),
            },
            "maturity": maturity,
        }
    )

ctrl_by_id = {record["control_id"]: record for record in controls}

test_specs = [
    (
        "TEST-001",
        "CTRL-RUNTIME-001",
        "CONTRACT",
        "Outbound disclosure allowlist excludes unauthorized fields",
        (
            "Unapproved identifying or recipient-inapplicable fields must not reach the "
            "final outbound payload."
        ),
        "An unapproved field exists in the final outbound payload.",
        (
            "request fixture; recipient/purpose policy snapshot; final outbound payload; "
            "decision evidence packet"
        ),
    ),
    (
        "TEST-002",
        "CTRL-RUNTIME-001",
        "FAILURE",
        "Purpose and recipient mismatch fails closed",
        "A transfer with mismatched purpose or recipient must be blocked or routed to review.",
        "Mismatched purpose or recipient is allowed without review.",
        "negative transfer fixture; routing decision trace; audit trace",
    ),
    (
        "TEST-003",
        "CTRL-RUNTIME-002",
        "ADVERSARIAL",
        "Re-identification purpose adversarial detection",
        (
            "Re-identification intent must be detected across direct and indirect "
            "prompt/request forms."
        ),
        "A re-identification request reaches execution without block or review.",
        "adversarial request set; classifier output; decision trace",
    ),
    (
        "TEST-004",
        "CTRL-RUNTIME-003",
        "INTEGRATION",
        "Mapping material cannot exit vault boundary",
        "Mapping keys or re-identification material must not be included in outbound payloads.",
        "Mapping material is present outside the approved vault boundary.",
        "vault access log; outbound payload; deny decision packet",
    ),
    (
        "TEST-005",
        "CTRL-EVAL-001",
        "GOLDEN",
        "Transform option evaluation compares privacy and utility",
        "Candidate transform options must be compared before any transform is promoted.",
        "A transform is selected without privacy and utility evaluation.",
        "privacy risk report; utility report; transform comparison table",
    ),
    (
        "TEST-006",
        "CTRL-GOV-001",
        "GOVERNANCE",
        "Pseudonymized processing review record exists",
        "Governance workflow must retain review and audit records for pseudonymized processing.",
        "No review or audit record exists for the processing case.",
        "review checklist; audit trace",
    ),
    (
        "TEST-007",
        "CTRL-GOV-002",
        "GOVERNANCE",
        "Consent request case is routed for handling",
        "Consent withdrawal or marketing contact cases must create a reviewable case record.",
        "No case record is created for a request requiring handling.",
        "case record; consent state snapshot",
    ),
    (
        "TEST-008",
        "CTRL-GOV-003",
        "GOVERNANCE",
        "Provider contract evidence is attached",
        "Outsourcing processing must have provider and contract review evidence before approval.",
        "Provider processing proceeds without contract or supervision evidence.",
        "contract checklist; provider assessment",
    ),
    (
        "TEST-009",
        "CTRL-RUNTIME-004",
        "CONTRACT",
        "Cross-border destination requires transfer basis",
        "Cross-border outbound flow must include transfer basis and destination metadata.",
        "Outbound cross-border payload is routed without transfer basis metadata.",
        "destination fixture; transfer basis record; outbound decision trace",
    ),
    (
        "TEST-010",
        "CTRL-RUNTIME-004",
        "GOVERNANCE",
        "Notice dependency is present where required",
        "Notice or review artifacts must be attached when the requirement depends on notice.",
        "Transfer review lacks required notice artifact.",
        "notice artifact; review record",
    ),
    (
        "TEST-011",
        "CTRL-REF-001",
        "GOVERNANCE",
        "General references remain review-only",
        "Reference-only requirements must create review context and no runtime decision.",
        "A runtime policy candidate is generated from reference-only requirements.",
        "traceability report; policy candidate inventory",
    ),
    (
        "TEST-012",
        "CTRL-REF-002",
        "GOVERNANCE",
        "Unverified electronic finance reference is blocked from promotion",
        "REVIEW_REQUIRED reference must remain in backlog until source verification.",
        "Dependent control or policy is promoted without source verification.",
        "evidence backlog item; source verification result",
    ),
    (
        "TEST-013",
        "CTRL-GOV-004",
        "GOVERNANCE",
        "Security monitoring evidence is retained",
        "Monitoring governance must retain policy, log, and review evidence.",
        "Monitoring control lacks audit or review record.",
        "monitoring policy; audit log; review record",
    ),
    (
        "TEST-014",
        "CTRL-RUNTIME-005",
        "UNIT",
        "Privileged account allowlist is enforced",
        "Only approved privileged accounts may access protected administration flows.",
        "Unapproved privileged account gains access.",
        "account inventory; access policy; negative access fixture",
    ),
    (
        "TEST-015",
        "CTRL-RUNTIME-005",
        "REPLAY",
        "Admin account event is auditable",
        "Privileged account decisions must be replayable from audit traces.",
        "Access decision cannot be reconstructed from audit trace.",
        "audit trace; decision packet",
    ),
    (
        "TEST-016",
        "CTRL-RUNTIME-006",
        "INTEGRATION",
        "External network path is denied or reviewed",
        "Unsupported internal-system external network path must not proceed silently.",
        "Unsupported external path succeeds without denial or review.",
        "network path fixture; connection decision log",
    ),
    (
        "TEST-017",
        "CTRL-RUNTIME-007",
        "UNIT",
        "Credential and regulated-data detector flags protected fields",
        "Credential or regulated-data fields must be detected before egress or storage handling.",
        "Protected field is not detected in fixture.",
        "secret fixture; scan report",
    ),
    (
        "TEST-018",
        "CTRL-RUNTIME-007",
        "CONTRACT",
        "Protection evidence is attached before routing",
        "Protected data routing must include protection evidence.",
        "Protected data is routed without protection evidence.",
        "protected payload evidence; policy snapshot",
    ),
    (
        "TEST-019",
        "CTRL-REF-003",
        "GOVERNANCE",
        "AI scope references do not create runtime policy",
        "AI definition references must remain review context only.",
        "Runtime policy candidate is generated from definition-only references.",
        "AI scope traceability report; policy candidate inventory",
    ),
    (
        "TEST-020",
        "CTRL-GOV-005",
        "GOVERNANCE",
        "AI usage monitoring record exists",
        "AI usage involving important data must have monitoring or review records.",
        "AI usage record lacks monitoring or review evidence.",
        "AI usage register; monitoring log",
    ),
    (
        "TEST-021",
        "CTRL-RUNTIME-008",
        "ADVERSARIAL",
        "Sensitive AI input detector catches labeled sensitive examples",
        "Labeled sensitive AI inputs must be detected before external routing.",
        "Sensitive labeled input reaches external AI without detection.",
        "labeled input fixture; detector report; decision trace",
    ),
    (
        "TEST-022",
        "CTRL-RUNTIME-008",
        "GOLDEN",
        "Transform options remain candidates until evaluated",
        "Candidate transform options must not be marked final without evaluation artifacts.",
        "A final transform appears without evaluation artifact.",
        "transform option list; evaluation dependency report",
    ),
    (
        "TEST-023",
        "CTRL-RUNTIME-009",
        "CONTRACT",
        "Provider reuse restriction is checked before routing",
        "External AI routing must verify provider/model-improvement reuse restriction dependency.",
        "Request is routed without provider reuse evidence.",
        "provider terms snapshot; routing decision trace",
    ),
    (
        "TEST-024",
        "CTRL-GOV-006",
        "GOVERNANCE",
        "SaaS provider review packet exists",
        "SaaS/cloud provider use must retain provider and security review artifacts.",
        "SaaS use proceeds without provider review packet.",
        "provider assessment; cloud security checklist",
    ),
    (
        "TEST-025",
        "CTRL-GOV-006",
        "FAILURE",
        "Unverified SaaS requirements block promotion",
        "REVIEW_REQUIRED SaaS requirements must prevent dependent promotion.",
        "Dependent policy is promoted with unresolved SaaS review requirements.",
        "evidence backlog item; validation report",
    ),
    (
        "TEST-026",
        "CTRL-GOV-007",
        "GOVERNANCE",
        "Digital asset safeguarding review is retained",
        (
            "Digital asset safeguarding requirements must produce review evidence, not "
            "runtime policy by default."
        ),
        "Runtime policy is generated without safeguarding review basis.",
        "safeguarding review packet; traceability report",
    ),
    (
        "TEST-027",
        "CTRL-REF-004",
        "GOVERNANCE",
        "Digital asset REVIEW_REQUIRED references remain backlog",
        "Unverified digital asset references must remain non-runtime until verified.",
        "Dependent policy is promoted before source verification.",
        "source verification result; evidence backlog item",
    ),
    (
        "TEST-028",
        "CTRL-RUNTIME-010",
        "UNIT",
        "Wallet and CDD field classifier separates field classes",
        "Wallet, transaction, and CDD fields must be classified into separate field groups.",
        "Wallet or CDD field is not classified or is mixed with unrelated fields.",
        "wallet/CDD fixture; field classification report",
    ),
    (
        "TEST-029",
        "CTRL-RUNTIME-010",
        "CONTRACT",
        "Digital asset field routing is auditable",
        "Digital asset field routing must produce an audit trace and decision packet.",
        "Field routing occurs without audit trace.",
        "audit trace; decision evidence packet",
    ),
]


def test_status(control_id: str) -> str:
    control = ctrl_by_id[control_id]
    return "VALIDATION_REQUIRED" if control["maturity"] == "VALIDATION_REQUIRED" else "DEFINED"


tests = [
    {
        "test_id": test_id,
        "control_ids": [control_id],
        "test_type": test_type,
        "test_name": name,
        "expected_behavior": expected,
        "failure_condition": failure,
        "required_artifact": artifact,
        "status": test_status(control_id),
    }
    for test_id, control_id, test_type, name, expected, failure, artifact in test_specs
]

ctrl_to_tests = defaultdict(list)
for test in tests:
    for control_id in test["control_ids"]:
        ctrl_to_tests[control_id].append(test["test_id"])


def req_maturity(requirement_ids: list[str]) -> str:
    statuses = [
        ev_by_id[req_by_id[req_id]["evidence_id"]].get("review_status")
        for req_id in requirement_ids
    ]
    return "REVIEW_REQUIRED" if "REVIEW_REQUIRED" in statuses else "VERIFIED"


def scopes(requirement_ids: list[str], field: str) -> list[str]:
    values = []
    for requirement_id in requirement_ids:
        applicability = req_by_id[requirement_id].get("applicability", {})
        candidates = (
            [applicability.get("actor", "")] if field == "actor" else applicability.get(field, [])
        )
        for value in candidates:
            if value and value not in values:
                values.append(value)
    return values


policy_specs = [
    (
        "PC-001",
        ["CTRL-RUNTIME-001"],
        "REVIEW",
        "NONE",
        [],
        (
            "Outbound transfer requires purpose/recipient guard; final BLOCK is not "
            "asserted until policy validation."
        ),
    ),
    (
        "PC-002",
        ["CTRL-RUNTIME-002"],
        "UNRESOLVED",
        "NONE",
        [],
        (
            "Re-identification detection is runtime-relevant, but action requires "
            "classifier validation."
        ),
    ),
    (
        "PC-003",
        ["CTRL-RUNTIME-003"],
        "REVIEW",
        "NONE",
        ["VAULT-TOKEN", "FIELD-SEPARATION"],
        "Mapping separation is runtime-relevant; concrete vault/token design requires evaluation.",
    ),
    (
        "PC-004",
        ["CTRL-EVAL-001"],
        "UNRESOLVED",
        "UNRESOLVED",
        ["MASK", "HMAC-PSEUDO", "VAULT-TOKEN", "GENERALIZE", "REMOVE", "KEEP"],
        "Transform choice is evaluation-dependent and cannot be final here.",
    ),
    (
        "PC-005",
        ["CTRL-RUNTIME-004"],
        "REVIEW",
        "NONE",
        [],
        (
            "Cross-border egress requires review gate; final action depends on transfer "
            "basis validation."
        ),
    ),
    (
        "PC-006",
        ["CTRL-RUNTIME-005"],
        "REVIEW",
        "NONE",
        [],
        "Privileged account control has REVIEW_REQUIRED dependencies and cannot be promoted.",
    ),
    (
        "PC-007",
        ["CTRL-RUNTIME-006"],
        "REVIEW",
        "NONE",
        [],
        "Network boundary control is runtime-relevant but final block policy requires validation.",
    ),
    (
        "PC-008",
        ["CTRL-RUNTIME-007"],
        "REVIEW",
        "NONE",
        ["FIELD-SEPARATION", "KEEP"],
        (
            "Protection control is runtime-relevant but encryption implementation is not "
            "selected here."
        ),
    ),
    (
        "PC-009",
        ["CTRL-RUNTIME-008"],
        "UNRESOLVED",
        "UNRESOLVED",
        ["MASK", "HMAC-PSEUDO", "VAULT-TOKEN", "GENERALIZE", "REMOVE", "KEEP"],
        "Sensitive AI input handling depends on detector and transform evaluation.",
    ),
    (
        "PC-010",
        ["CTRL-RUNTIME-009"],
        "REVIEW",
        "NONE",
        [],
        "Provider reuse restriction requires provider evidence before external AI routing.",
    ),
    (
        "PC-011",
        ["CTRL-RUNTIME-010"],
        "REVIEW",
        "UNRESOLVED",
        ["FIELD-SEPARATION", "MASK", "KEEP"],
        (
            "Digital asset field separation is runtime-relevant, but REVIEW_REQUIRED wallet "
            "evidence blocks promotion."
        ),
    ),
]

policies = []
for policy_id, control_ids, action, transform, transform_options, rationale in policy_specs:
    requirement_ids = sorted(
        {
            req_id
            for control_id in control_ids
            for req_id in ctrl_by_id[control_id]["requirement_ids"]
        }
    )
    maturity = req_maturity(requirement_ids)
    dependencies = {"runtime_policy_validation"}
    if maturity == "REVIEW_REQUIRED":
        dependencies.add("evidence_backlog_resolution")
    if transform != "NONE" or transform_options:
        dependencies.add("data_evaluation_artifact")
    policies.append(
        {
            "policy_candidate_id": policy_id,
            "requirement_ids": requirement_ids,
            "control_ids": control_ids,
            "test_ids": sorted(
                {test_id for control_id in control_ids for test_id in ctrl_to_tests[control_id]}
            ),
            "workload_scope": scopes(requirement_ids, "processing_context"),
            "actor_scope": scopes(requirement_ids, "actor"),
            "purpose_scope": sorted(
                {
                    req_by_id[req_id].get("source_derived_requirement", {}).get("condition", "")
                    for req_id in requirement_ids
                    if req_by_id[req_id].get("source_derived_requirement", {}).get("condition", "")
                }
            ),
            "processing_phase": scopes(requirement_ids, "processing_context"),
            "data_class": scopes(requirement_ids, "data"),
            "applicability": (
                "Candidate applicability derived from linked Requirement Candidates; "
                "not an active runtime policy."
            ),
            "conditions": sorted(
                {
                    req_by_id[req_id].get("source_derived_requirement", {}).get("condition", "")
                    for req_id in requirement_ids
                    if req_by_id[req_id].get("source_derived_requirement", {}).get("condition", "")
                }
            ),
            "candidate_action": action,
            "candidate_transform": transform,
            "candidate_transform_options": transform_options,
            "reason_codes": sorted(
                {rule for req_id in requirement_ids for rule in req_to_legacy.get(req_id, [])}
            )
            + ["REQUIREMENT_DERIVED_CANDIDATE"],
            "evidence_maturity": maturity,
            "policy_maturity": "VALIDATION_REQUIRED",
            "validation_dependencies": sorted(dependencies),
            "promotion_blocked": maturity == "REVIEW_REQUIRED",
            "status": "VALIDATION_REQUIRED",
            "rationale": rationale,
        }
    )

traceability = []
for control in controls:
    for requirement_id in control["requirement_ids"]:
        requirement = req_by_id[requirement_id]
        traceability.append(
            {
                "official_source_id": ev_by_id[requirement["evidence_id"]].get("source_id"),
                "evidence_id": requirement["evidence_id"],
                "requirement_id": requirement_id,
                "control_id": control["control_id"],
                "test_ids": sorted(
                    {
                        test["test_id"]
                        for test in tests
                        if control["control_id"] in test["control_ids"]
                    }
                ),
                "policy_candidate_ids": sorted(
                    {
                        policy["policy_candidate_id"]
                        for policy in policies
                        if control["control_id"] in policy["control_ids"]
                    }
                ),
                "legacy_rule_ids": sorted(req_to_legacy.get(requirement_id, [])),
            }
        )

legacy_mapping = []
for legacy_rule_id in sorted(legacy_by_id):
    rule = legacy_by_id[legacy_rule_id]
    requirement_ids = sorted(
        {
            ev_to_req[evidence_id]
            for evidence_id in rule.get("evidence_refs", [])
            if evidence_id in ev_to_req
        }
    )
    legacy_mapping.append(
        {
            "legacy_rule_id": legacy_rule_id,
            "requirement_ids": requirement_ids,
            "migration_role": "PROVENANCE_ONLY",
            "audit_classification": (
                "REQUIRES_REDESIGN"
                if legacy_rule_id == "GR-0008"
                else (
                    "NEEDS_REVIEW"
                    if legacy_rule_id
                    in {"GR-0001", "GR-0002", "GR-0003", "GR-0004", "GR-0007", "GR-0009", "GR-0010"}
                    else (
                        "DEFER"
                        if legacy_rule_id in {"GR-0018", "GR-0019", "GR-0021", "GR-0022"}
                        else "MIGRATABLE"
                    )
                )
            ),
            "review_required_evidence_ids": [
                evidence_id
                for evidence_id in rule.get("evidence_refs", [])
                if evidence_id in review_required_evidence
            ],
            "note": (
                "Legacy GR is preserved as provenance. New Control/Test/Policy objects "
                "are derived from "
                "Requirement Candidate grouping, not GR 1:1 migration."
            ),
        }
    )

downstream_todo = [
    {
        "item": "GR-0008 decomposed at Requirement level, not as a legacy control.",
        "status": "DEFERRED_DESIGN_WORK",
        "next_step": (
            "Validate whether RC-00026/33/34/49 security governance and RC-00038/39 AI "
            "governance need separate promoted runtime policies."
        ),
    },
    {
        "item": "Transform options for CTRL-EVAL-001 and CTRL-RUNTIME-008 require data evaluation.",
        "status": "VALIDATION_REQUIRED",
        "next_step": (
            "Evaluate privacy risk, utility, and relationship preservation before selecting "
            "final transform."
        ),
    },
    {
        "item": (
            "REVIEW_REQUIRED requirements remain connected but block dependent promotion "
            "only where policy dependency exists."
        ),
        "status": "VALIDATION_REQUIRED",
        "next_step": "Resolve source verification backlog for RC-00025/27/29/46/47/53/54/55/56/57.",
    },
]

write(ROOT / "processed" / "requirement_classification.json", requirement_analysis)
write(ROOT / "processed" / "controls.json", controls)
write(ROOT / "processed" / "tests.json", tests)
write(ROOT / "processed" / "policy_candidates.json", policies)
write(ROOT / "processed" / "traceability.json", traceability)
write(ROOT / "migration" / "legacy_rule_mapping.json", legacy_mapping)
write(
    ROOT / "provisional" / "project_provisional_rules.json",
    [policy for policy in policies if not policy["promotion_blocked"]],
)
write(ROOT / "review" / "downstream_todo.json", downstream_todo)
