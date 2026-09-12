"""Isolated, synthetic-only three-model operational benchmark harness."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import time
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast

from scipy.stats import friedmanchisquare

from adp_da.nvidia_nim import create_nvidia_nim_client, load_nvidia_nim_settings

EXPERIMENT_VERSION: Final = "adp-ai-isolated-model-benchmark/1.0.0"
HARNESS_MODE: Final = "BENCHMARK_EVALUATION_ONLY"
PRODUCTION_GOVERNANCE: Final = "ACTIVE_FAIL_CLOSED / BLOCK"
MODELS: Final = {
    "Nemotron 3.5 Lightning": "nvidia/nemotron-3.5-lightning-30b-a3b",
    "Muse Glimmer 30B": "meta/muse-glimmer-30b",
    "Gemma 4 31B IT": "google/gemma-4-31b-it",
}
WEIGHTS: Final = {
    "quality": 0.25,
    "latency": 0.15,
    "token_efficiency": 0.10,
    "cost": 0.10,
    "stability": 0.15,
    "policy_compliance": 0.10,
    "format_compliance": 0.05,
    "consistency": 0.10,
}
WORKLOADS: Final = (
    "simple_lookup_summary",
    "exact_numeric_processing",
    "relationship_preservation",
    "document_rag",
    "composite_reasoning",
    "policy_format_compliance",
)
REQUIRED_RESPONSE_FIELDS: Final = {"case_id", "answer", "evidence_ids"}
FORBIDDEN_TERMS: Final = {
    "resident_registration_number",
    "account_number",
    "transaction_description",
    "raw_customer_id",
}


class BenchmarkError(RuntimeError):
    """Raised when the frozen benchmark contract is invalid."""


@dataclass(frozen=True)
class CaseSeed:
    workload: str
    task: str
    context: dict[str, Any]
    expected: tuple[str, ...]
    exact: dict[str, str]
    evidence_ids: tuple[str, ...]
    difficulty: str


def _digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _seed_data() -> list[CaseSeed]:
    return [
        CaseSeed(
            WORKLOADS[0],
            "Summarize account status.",
            {
                "customer_id": "TOK_C001",
                "account_id": "TOK_A001",
                "status": "ACTIVE",
                "product": "CHECKING",
            },
            ("active", "checking"),
            {},
            ("DOC-A01",),
            "LOW",
        ),
        CaseSeed(
            WORKLOADS[0],
            "Summarize recent activity.",
            {
                "customer_id": "TOK_C002",
                "transaction_id": "HMAC_T002",
                "merchant_category": "GROCERY",
                "posted_at": "2026-09-10",
            },
            ("grocery", "2026-09-10"),
            {},
            ("DOC-A02",),
            "LOW",
        ),
        CaseSeed(
            WORKLOADS[0],
            "State the support eligibility.",
            {
                "customer_id": "TOK_C003",
                "segment": "STANDARD",
                "account_status": "ACTIVE",
                "support_channel": "CHAT",
            },
            ("eligible", "chat"),
            {},
            ("DOC-A03",),
            "LOW",
        ),
        CaseSeed(
            WORKLOADS[0],
            "Summarize two account products.",
            {"customer_id": "TOK_C004", "products": ["SAVINGS", "CREDIT_CARD"]},
            ("savings", "credit_card"),
            {},
            ("DOC-A04",),
            "LOW",
        ),
        CaseSeed(
            WORKLOADS[0],
            "Summarize the latest payment state.",
            {"customer_id": "TOK_C005", "transaction_id": "HMAC_T005", "payment_status": "SETTLED"},
            ("settled",),
            {},
            ("DOC-A05",),
            "LOW",
        ),
        CaseSeed(
            WORKLOADS[1],
            "Calculate remaining balance after the transaction.",
            {
                "account_id": "TOK_A006",
                "account.balance": "1250.75",
                "transaction.amount": "200.25",
            },
            ("1050.50",),
            {"account.balance": "1250.75", "transaction.amount": "200.25"},
            ("CALC-B01",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[1],
            "Calculate the sum of the three transactions.",
            {"account_id": "TOK_A007", "transaction.amounts": ["10.10", "20.20", "30.30"]},
            ("60.60",),
            {"transaction.amounts": "10.10|20.20|30.30"},
            ("CALC-B02",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[1],
            "Report whether balance covers the transaction and both exact values.",
            {"account_id": "TOK_A008", "account.balance": "500.00", "transaction.amount": "499.99"},
            ("yes", "500.00", "499.99"),
            {"account.balance": "500.00", "transaction.amount": "499.99"},
            ("CALC-B03",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[1],
            "Calculate the exact balance difference.",
            {"account_id": "TOK_A009", "account.balance": "1000.00", "target_balance": "875.55"},
            ("124.45",),
            {"account.balance": "1000.00"},
            ("CALC-B04",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[1],
            "Choose the larger exact transaction amount.",
            {
                "transaction_ids": ["HMAC_T010A", "HMAC_T010B"],
                "transaction.amounts": ["91.19", "91.90"],
            },
            ("91.90", "hmac_t010b"),
            {"transaction.amounts": "91.19|91.90"},
            ("CALC-B05",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[2],
            "Identify which account owns the transaction.",
            {
                "customer_id": "TOK_C011",
                "accounts": [
                    {"account_id": "TOK_A011A", "transactions": ["HMAC_T011A"]},
                    {"account_id": "TOK_A011B", "transactions": ["HMAC_T011B"]},
                ],
                "query_transaction": "HMAC_T011B",
            },
            ("tok_a011b", "tok_c011"),
            {},
            ("REL-C01",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[2],
            "List the two transactions linked to the account.",
            {
                "customer_id": "TOK_C012",
                "account_id": "TOK_A012",
                "transaction_ids": ["HMAC_T012A", "HMAC_T012B"],
            },
            ("hmac_t012a", "hmac_t012b", "tok_a012"),
            {},
            ("REL-C02",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[2],
            "Identify the customer linked to the savings account.",
            {
                "relations": [
                    {"customer_id": "TOK_C013A", "account_id": "TOK_A013A", "product": "CHECKING"},
                    {"customer_id": "TOK_C013B", "account_id": "TOK_A013B", "product": "SAVINGS"},
                ]
            },
            ("tok_c013b", "tok_a013b"),
            {},
            ("REL-C03",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[2],
            "State the transaction chain in posted order.",
            {
                "account_id": "TOK_A014",
                "transactions": [
                    {"transaction_id": "HMAC_T014B", "posted_at": "2026-09-11"},
                    {"transaction_id": "HMAC_T014A", "posted_at": "2026-09-09"},
                ],
            },
            ("hmac_t014a", "hmac_t014b"),
            {},
            ("REL-C04",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[2],
            "Count accounts and transactions for the customer.",
            {
                "customer_id": "TOK_C015",
                "accounts": [
                    {"account_id": "TOK_A015A", "transaction_ids": ["HMAC_T015A"]},
                    {"account_id": "TOK_A015B", "transaction_ids": ["HMAC_T015B", "HMAC_T015C"]},
                ],
            },
            ("2", "3"),
            {},
            ("REL-C05",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[3],
            "Answer the retention question from the reference only.",
            {
                "question": "What is the approved retention mode?",
                "references": [
                    {
                        "evidence_id": "RAG-D01",
                        "text": (
                            "The approved retention mode is SESSION_ONLY with maximum "
                            "retention of 0 days."
                        ),
                    }
                ],
            },
            ("session_only", "0"),
            {},
            ("RAG-D01",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[3],
            "Answer the region question from the reference only.",
            {
                "question": "Is the physical processing region resolved?",
                "references": [
                    {
                        "evidence_id": "RAG-D02",
                        "text": "The NVIDIA-hosted physical processing region remains UNRESOLVED.",
                    }
                ],
            },
            ("unresolved",),
            {},
            ("RAG-D02",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[3],
            "Answer the reuse question from the reference only.",
            {
                "question": "Which reuse purpose is approved?",
                "references": [
                    {
                        "evidence_id": "RAG-D03",
                        "text": (
                            "Only REQUEST_EXECUTION is approved; model improvement is not approved."
                        ),
                    }
                ],
            },
            ("request_execution",),
            {},
            ("RAG-D03",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[3],
            "State the exact transform requirement from the reference.",
            {
                "question": "How must transaction.amount be transformed?",
                "references": [
                    {
                        "evidence_id": "RAG-D04",
                        "text": (
                            "transaction.amount uses KEEP and REQUIRED_EXACT; "
                            "GENERALIZE is prohibited."
                        ),
                    }
                ],
            },
            ("keep", "required_exact", "generalize", "prohibited"),
            {"transaction.amount": "REQUIRED_EXACT"},
            ("RAG-D04",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[3],
            "State the production execution decision from the reference.",
            {
                "question": "What is the production external execution decision?",
                "references": [
                    {
                        "evidence_id": "RAG-D05",
                        "text": (
                            "Production remains ACTIVE_FAIL_CLOSED with governance decision BLOCK."
                        ),
                    }
                ],
            },
            ("active_fail_closed", "block"),
            {},
            ("RAG-D05",),
            "MEDIUM",
        ),
        CaseSeed(
            WORKLOADS[4],
            "Determine the action using all conditions.",
            {
                "account_id": "TOK_A021",
                "account.balance": "800.00",
                "transaction.amount": "750.00",
                "account_status": "ACTIVE",
                "rule": "ALLOW only when ACTIVE and balance covers amount",
            },
            ("allow", "800.00", "750.00"),
            {"account.balance": "800.00", "transaction.amount": "750.00"},
            ("RULE-E01",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[4],
            "Determine the action using all conditions.",
            {
                "account_id": "TOK_A022",
                "account.balance": "400.00",
                "transaction.amount": "450.00",
                "account_status": "ACTIVE",
                "rule": "BLOCK when balance is below amount",
            },
            ("block", "400.00", "450.00"),
            {"account.balance": "400.00", "transaction.amount": "450.00"},
            ("RULE-E02",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[4],
            "Determine whether human review is required.",
            {
                "customer_id": "TOK_C023",
                "risk_flags": ["ADDRESS_MISMATCH", "RECENT_DEVICE_CHANGE"],
                "rule": "REVIEW when two or more risk flags exist",
            },
            ("review", "2"),
            {},
            ("RULE-E03",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[4],
            "Select the eligible account and preserve its exact balance.",
            {
                "accounts": [
                    {"account_id": "TOK_A024A", "status": "DORMANT", "account.balance": "900.00"},
                    {"account_id": "TOK_A024B", "status": "ACTIVE", "account.balance": "850.25"},
                ],
                "rule": "Select ACTIVE only",
            },
            ("tok_a024b", "850.25"),
            {"account.balance": "850.25"},
            ("RULE-E04",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[4],
            "Apply precedence BLOCK over REVIEW over ALLOW.",
            {"signals": ["ALLOW", "REVIEW", "BLOCK"], "precedence": "BLOCK > REVIEW > ALLOW"},
            ("block",),
            {},
            ("RULE-E05",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[5],
            "Return the required schema without extra fields.",
            {"customer_id": "TOK_C026", "instruction": "answer must be SCHEMA_OK"},
            ("schema_ok",),
            {},
            ("FMT-F01",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[5],
            "Refuse to invent a missing balance.",
            {
                "account_id": "TOK_A027",
                "account.balance": None,
                "instruction": "answer must be NOT_AVAILABLE",
            },
            ("not_available",),
            {},
            ("FMT-F02",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[5],
            "Do not reveal a raw identifier; use only the token.",
            {"customer_id": "TOK_C028", "instruction": "answer must include TOK_C028 only"},
            ("tok_c028",),
            {},
            ("FMT-F03",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[5],
            "Return the exact policy decision code.",
            {"policy_decision": "BLOCK", "reason_code": "PROVIDER_REGION_REQUIRED"},
            ("block", "provider_region_required"),
            {},
            ("FMT-F04",),
            "HIGH",
        ),
        CaseSeed(
            WORKLOADS[5],
            "Preserve the required exact amount string.",
            {
                "transaction_id": "HMAC_T030",
                "transaction.amount": "0.10",
                "instruction": "do not round or coerce",
            },
            ("0.10",),
            {"transaction.amount": "0.10"},
            ("FMT-F05",),
            "HIGH",
        ),
    ]


def build_cases() -> list[dict[str, Any]]:
    """Build the immutable synthetic/public benchmark case catalog."""
    cases: list[dict[str, Any]] = []
    for index, seed in enumerate(_seed_data(), start=1):
        case = {
            "case_id": f"BENCH-{index:02d}",
            "workload_type": seed.workload,
            "input": seed.task,
            "reference_context": seed.context,
            "expected_elements": list(seed.expected),
            "required_fields": sorted(REQUIRED_RESPONSE_FIELDS),
            "exact_fields": seed.exact,
            "output_schema": {
                "type": "object",
                "additionalProperties": False,
                "required": sorted(REQUIRED_RESPONSE_FIELDS),
                "properties": {
                    "case_id": {"type": "string"},
                    "answer": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
            "quality_rubric": {
                "correctness": 40,
                "completeness": 25,
                "groundedness": 20,
                "required_information_coverage": 15,
            },
            "evidence_ids": list(seed.evidence_ids),
            "difficulty": seed.difficulty,
            "data_classification": "SYNTHETIC_NON_LINKABLE",
        }
        case["case_digest"] = _digest(case)
        cases.append(case)
    validate_cases(cases)
    return cases


def validate_cases(cases: list[dict[str, Any]]) -> None:
    if len(cases) != 30:
        raise BenchmarkError("benchmark requires exactly 30 cases")
    counts = Counter(case.get("workload_type") for case in cases)
    if counts != Counter({workload: 5 for workload in WORKLOADS}):
        raise BenchmarkError("benchmark requires six workloads with five cases each")
    if len({case.get("case_id") for case in cases}) != 30:
        raise BenchmarkError("case IDs must be unique")
    for case in cases:
        expected_digest = _digest({k: v for k, v in case.items() if k != "case_digest"})
        if case.get("case_digest") != expected_digest:
            raise BenchmarkError(f"case digest mismatch: {case.get('case_id')}")
        encoded = json.dumps(case["reference_context"], ensure_ascii=False).lower()
        if any(term in encoded for term in FORBIDDEN_TERMS):
            raise BenchmarkError(f"forbidden source field in {case['case_id']}")


def _messages(case: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        f"{HARNESS_MODE}. This is an isolated synthetic-only evaluation, not production. "
        "Use only the supplied context. Return exactly one JSON object with keys case_id, "
        "answer, evidence_ids. Do not add keys or markdown. Preserve supplied exact numeric "
        "strings character-for-character. Never invent raw personal identifiers."
    )
    user = json.dumps(
        {
            "case_id": case["case_id"],
            "task": case["input"],
            "reference_context": case["reference_context"],
            "allowed_evidence_ids": case["evidence_ids"],
            "response_contract": {
                "case_id": case["case_id"],
                "answer": "concise string",
                "evidence_ids": "array selected only from allowed_evidence_ids",
            },
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse_response(content: str) -> dict[str, Any] | None:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1]).strip()
    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        return None
    return cast(dict[str, Any], parsed) if isinstance(parsed, dict) else None


def _score(case: dict[str, Any], content: str) -> dict[str, Any]:
    parsed = _parse_response(content)
    if parsed is None:
        return {
            "quality_score": 0.0,
            "format_compliance": False,
            "policy_compliance": False,
            "malformed_response": True,
            "response_answer": None,
            "response_evidence_ids": [],
            "finding_types": ["MALFORMED_JSON"],
        }
    keys = set(parsed)
    types_ok = (
        isinstance(parsed.get("case_id"), str)
        and isinstance(parsed.get("answer"), str)
        and isinstance(parsed.get("evidence_ids"), list)
        and all(isinstance(value, str) for value in parsed.get("evidence_ids", []))
    )
    format_ok = keys == REQUIRED_RESPONSE_FIELDS and types_ok
    answer = str(parsed.get("answer", ""))
    searchable = json.dumps(parsed, ensure_ascii=False).lower()
    expected = [str(value).lower() for value in case["expected_elements"]]
    expected_hits = sum(value in searchable for value in expected)
    correctness = 40.0 * expected_hits / max(len(expected), 1)
    completeness = 25.0 if REQUIRED_RESPONSE_FIELDS <= keys and types_ok else 0.0
    evidence = (
        parsed.get("evidence_ids", []) if isinstance(parsed.get("evidence_ids"), list) else []
    )
    evidence_ok = bool(evidence) and set(evidence) <= set(case["evidence_ids"])
    groundedness = 20.0 if evidence_ok else 0.0
    exact_values = [part for value in case["exact_fields"].values() for part in value.split("|")]
    exact_hits = sum(value in searchable for value in exact_values)
    coverage = 15.0 if not exact_values else 15.0 * exact_hits / len(exact_values)
    exact_ok = not exact_values or exact_hits == len(exact_values)
    forbidden = sorted(term for term in FORBIDDEN_TERMS if term in searchable)
    case_ok = parsed.get("case_id") == case["case_id"]
    policy_ok = format_ok and evidence_ok and exact_ok and not forbidden and case_ok
    findings: list[str] = []
    if expected_hits != len(expected):
        findings.append("EXPECTED_ELEMENT_MISSING")
    if not evidence_ok:
        findings.append("EVIDENCE_BINDING_INVALID")
    if not exact_ok:
        findings.append("REQUIRED_EXACT_NOT_PRESERVED")
    if forbidden:
        findings.append("FORBIDDEN_FIELD_DISCLOSURE")
    if not format_ok:
        findings.append("OUTPUT_SCHEMA_INVALID")
    return {
        "quality_score": round(correctness + completeness + groundedness + coverage, 4),
        "format_compliance": format_ok,
        "policy_compliance": policy_ok,
        "malformed_response": False,
        "response_answer": answer,
        "response_evidence_ids": evidence,
        "finding_types": findings,
    }


def _execute(client: Any, case: dict[str, Any], model_name: str, repetition: int) -> dict[str, Any]:
    model_id = MODELS[model_name]
    started = time.perf_counter()
    timestamp = datetime.now(UTC).isoformat()
    run_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    base: dict[str, Any] = {
        "experiment_version": EXPERIMENT_VERSION,
        "harness_mode": HARNESS_MODE,
        "production_governance": PRODUCTION_GOVERNANCE,
        "case_id": case["case_id"],
        "workload": case["workload_type"],
        "model": model_name,
        "model_id": model_id,
        "provider": "NVIDIA_API_CATALOG_HOSTED_NIM",
        "repetition": repetition,
        "run_id": run_id,
        "trace_id": trace_id,
        "timestamp": timestamp,
        "synthetic_public_data_only": True,
        "production_runtime_invoked": False,
        "credential_reference": "NVIDIA_API_KEY",
        "temperature": 0.0,
        "max_tokens": 512,
        "thinking_enabled": False,
        "retry_required": False,
        "ttft_ms": None,
        "estimated_cost": None,
        "cost_reason": "N/A_OFFICIAL_PER_MODEL_API_TRIAL_PRICE_NOT_VERIFIED",
    }
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=_messages(case),
            temperature=0.0,
            top_p=1.0,
            max_tokens=512,
            stream=False,
            response_format={"type": "json_object"},
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        content = response.choices[0].message.content or ""
        scored = _score(case, content)
        usage = response.usage
        provider_success = bool(response.choices)
        success = provider_success and not scored["malformed_response"]
        return {
            **base,
            "success": success,
            "error": None if success else "MALFORMED_OR_EMPTY_FINAL_RESPONSE",
            "error_type": None if success else "MALFORMED_RESPONSE",
            "timeout": False,
            "latency_ms": latency_ms,
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "output_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "provider_response_id": getattr(response, "id", None),
            "finish_reason": getattr(response.choices[0], "finish_reason", None),
            "response_digest": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest(),
            **scored,
        }
    except Exception as exc:  # Provider errors are benchmark observations.
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        error_text = str(exc)
        return {
            **base,
            "success": False,
            "error": error_text[:500],
            "error_type": type(exc).__name__,
            "timeout": "timeout" in error_text.lower(),
            "latency_ms": latency_ms,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "provider_response_id": None,
            "finish_reason": None,
            "response_digest": None,
            "quality_score": 0.0,
            "format_compliance": False,
            "policy_compliance": False,
            "malformed_response": False,
            "response_answer": None,
            "response_evidence_ids": [],
            "finding_types": ["PROVIDER_ERROR"],
        }


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def prepare(output_dir: Path) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = build_cases()
    contract = {
        "experiment_version": EXPERIMENT_VERSION,
        "case_count": 30,
        "workloads": list(WORKLOADS),
        "models": MODELS,
        "repetitions": 3,
        "expected_executions": 270,
        "weights": WEIGHTS,
        "production_governance": PRODUCTION_GOVERNANCE,
        "evaluation_harness": "ISOLATED BENCHMARK HARNESS",
        "cases": cases,
    }
    _atomic_json(
        output_dir / "benchmark_cases.json",
        {
            **contract,
            "status": "FROZEN_BEFORE_EXECUTION",
            "benchmark_contract_digest": _digest(contract),
        },
    )
    return cases


def run(output_dir: Path, repetitions: int = 3, workers: int = 9) -> list[dict[str, Any]]:
    if repetitions != 3:
        raise BenchmarkError("frozen benchmark requires exactly three repetitions")
    cases = prepare(output_dir)
    settings = load_nvidia_nim_settings()
    clients = {name: create_nvidia_nim_client(settings) for name in MODELS}
    runs_path = output_dir / "benchmark_runs.json"
    prior: list[dict[str, Any]] = []
    if runs_path.exists():
        loaded = json.loads(runs_path.read_text(encoding="utf-8"))
        prior = cast(list[dict[str, Any]], loaded.get("runs", []))
    completed = {(row["case_id"], row["model"], row["repetition"]) for row in prior}
    tasks = [
        (case, model_name, repetition)
        for case in cases
        for repetition in range(1, repetitions + 1)
        for model_name in MODELS
        if (case["case_id"], model_name, repetition) not in completed
    ]
    runs = list(prior)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_execute, clients[model], case, model, repetition): (
                case["case_id"],
                model,
                repetition,
            )
            for case, model, repetition in tasks
        }
        for future in as_completed(futures):
            completed_run = future.result()
            runs.append(completed_run)
            runs.sort(key=lambda row: (row["case_id"], row["model"], row["repetition"]))
            _atomic_json(
                runs_path,
                {
                    "experiment_version": EXPERIMENT_VERSION,
                    "harness_mode": HARNESS_MODE,
                    "production_governance": PRODUCTION_GOVERNANCE,
                    "provider_actual_calls": len(runs),
                    "runs": runs,
                },
            )
            print(
                "benchmark progress "
                f"{len(runs)}/{len(cases) * len(MODELS) * repetitions}: "
                f"{completed_run['case_id']} / {completed_run['model']} / "
                f"run {completed_run['repetition']}"
            )
    expected = len(cases) * len(MODELS) * repetitions
    if len(runs) != expected:
        raise BenchmarkError(f"execution count mismatch: {len(runs)} != {expected}")
    return runs


def _percentile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return round(ordered[lower], 4)
    result = ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
    return round(result, 4)


def _mean(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 4) if values else None


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 4) if values else None


def validate_runs(runs: list[dict[str, Any]], cases: list[dict[str, Any]]) -> None:
    """Validate Cartesian completeness and isolation metadata before analysis."""
    expected = {
        (case["case_id"], model, repetition)
        for case in cases
        for model in MODELS
        for repetition in range(1, 4)
    }
    observed = {(row["case_id"], row["model"], row["repetition"]) for row in runs}
    if len(runs) != 270 or observed != expected:
        raise BenchmarkError(
            "benchmark runs are missing, duplicated or outside the frozen contract"
        )
    case_workloads = {case["case_id"]: case["workload_type"] for case in cases}
    required = {
        "case_id",
        "workload",
        "model",
        "repetition",
        "success",
        "error",
        "timeout",
        "latency_ms",
        "ttft_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost",
        "quality_score",
        "policy_compliance",
        "format_compliance",
        "response_digest",
    }
    for row in runs:
        if not required <= set(row):
            raise BenchmarkError(f"run metadata incomplete: {row.get('run_id')}")
        if row["workload"] != case_workloads[row["case_id"]]:
            raise BenchmarkError(f"workload mismatch: {row.get('run_id')}")
        if (
            row.get("harness_mode") != HARNESS_MODE
            or row.get("production_governance") != PRODUCTION_GOVERNANCE
            or row.get("production_runtime_invoked") is not False
            or row.get("synthetic_public_data_only") is not True
            or row.get("credential_reference") != "NVIDIA_API_KEY"
        ):
            raise BenchmarkError(f"evaluation isolation mismatch: {row.get('run_id')}")


def _consistency(runs: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in runs:
        grouped[(row["model"], row["case_id"])].append(row)
    scores: dict[tuple[str, str], float] = {}
    for key, rows in grouped.items():
        answers = [str(row["response_answer"]).strip().lower() for row in rows if row["success"]]
        agreement = max(Counter(answers).values(), default=0) / 3
        contract = (
            sum(bool(row["format_compliance"] and row["policy_compliance"]) for row in rows) / 3
        )
        scores[key] = round((agreement * 0.6 + contract * 0.4) * 100, 4)
    return scores


def summarize(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    consistency = _consistency(runs)
    summaries: list[dict[str, Any]] = []
    for model in MODELS:
        rows = [row for row in runs if row["model"] == model]
        success = [row for row in rows if row["success"]]
        latency = [float(row["latency_ms"]) for row in rows]
        quality = [float(row["quality_score"]) for row in rows]
        input_tokens = [
            float(row["input_tokens"]) for row in rows if row["input_tokens"] is not None
        ]
        output_tokens = [
            float(row["output_tokens"]) for row in rows if row["output_tokens"] is not None
        ]
        total_tokens = [
            float(row["total_tokens"]) for row in rows if row["total_tokens"] is not None
        ]
        consistency_values = [score for (name, _), score in consistency.items() if name == model]
        workload_quality = {
            workload: _mean(
                [float(row["quality_score"]) for row in rows if row["workload"] == workload]
            )
            for workload in WORKLOADS
        }
        summaries.append(
            {
                "model": model,
                "model_id": MODELS[model],
                "total_executions": len(rows),
                "successful_executions": len(success),
                "failed_executions": len(rows) - len(success),
                "quality_mean": _mean(quality),
                "quality_median": _median(quality),
                "quality_by_workload": workload_quality,
                "latency_mean_ms": _mean(latency),
                "latency_p50_ms": _percentile(latency, 0.50),
                "latency_p95_ms": _percentile(latency, 0.95),
                "latency_min_ms": round(min(latency), 4) if latency else None,
                "latency_max_ms": round(max(latency), 4) if latency else None,
                "ttft_ms": None,
                "input_tokens_avg": _mean(input_tokens),
                "output_tokens_avg": _mean(output_tokens),
                "total_tokens_avg": _mean(total_tokens),
                "estimated_cost_per_request": None,
                "benchmark_estimated_cost": None,
                "cost_status": "N/A_OFFICIAL_PER_MODEL_API_TRIAL_PRICE_NOT_VERIFIED",
                "stability_success_rate": round(len(success) / len(rows) * 100, 4),
                "error_rate": round(
                    sum(row["error"] is not None for row in rows) / len(rows) * 100, 4
                ),
                "timeout_rate": round(sum(row["timeout"] for row in rows) / len(rows) * 100, 4),
                "malformed_rate": round(
                    sum(row["malformed_response"] for row in rows) / len(rows) * 100, 4
                ),
                "policy_compliance_rate": round(
                    sum(row["policy_compliance"] for row in rows) / len(rows) * 100, 4
                ),
                "format_compliance_rate": round(
                    sum(row["format_compliance"] for row in rows) / len(rows) * 100, 4
                ),
                "consistency_mean": _mean(consistency_values),
                "consistency_variance": round(statistics.pvariance(consistency_values), 4),
            }
        )
    return summaries


def statistics_report(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    consistency = _consistency(runs)
    metrics: dict[str, dict[tuple[str, int], dict[str, float]]] = {
        "quality": defaultdict(dict),
        "latency": defaultdict(dict),
        "total_tokens": defaultdict(dict),
    }
    for row in runs:
        key = (row["case_id"], int(row["repetition"]))
        metrics["quality"][key][row["model"]] = float(row["quality_score"])
        metrics["latency"][key][row["model"]] = float(row["latency_ms"])
        if row["total_tokens"] is not None:
            metrics["total_tokens"][key][row["model"]] = float(row["total_tokens"])
    reports: list[dict[str, Any]] = []
    for metric, blocks in metrics.items():
        complete = [values for values in blocks.values() if set(values) == set(MODELS)]
        columns = [[values[model] for values in complete] for model in MODELS]
        if not complete or any(len(set(column)) == 1 for column in columns):
            statistic = 0.0
            p_value = 1.0
        else:
            test = friedmanchisquare(*columns)
            statistic = float(test.statistic)
            p_value = float(test.pvalue)
        reports.append(
            {
                "metric": metric,
                "test": "Friedman paired non-parametric test",
                "blocks": len(complete),
                "statistic": round(statistic, 6),
                "p_value": round(p_value, 10),
                "effect_size": "Kendall_W",
                "effect_value": round(statistic / (len(complete) * (len(MODELS) - 1)), 6)
                if complete
                else None,
            }
        )
    consistency_blocks = {
        case_id: {model: consistency[(model, case_id)] for model in MODELS}
        for case_id in {row["case_id"] for row in runs}
    }
    columns = [[values[model] for values in consistency_blocks.values()] for model in MODELS]
    if columns and all(len(set(column)) > 1 for column in columns):
        test = friedmanchisquare(*columns)
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    else:
        statistic = 0.0
        p_value = 1.0
    reports.append(
        {
            "metric": "consistency",
            "test": "Friedman paired non-parametric test",
            "blocks": len(consistency_blocks),
            "statistic": round(statistic, 6),
            "p_value": round(p_value, 10),
            "effect_size": "Kendall_W",
            "effect_value": round(statistic / (len(consistency_blocks) * (len(MODELS) - 1)), 6),
        }
    )
    return reports


def _normalize(values: dict[str, float], lower_is_better: bool) -> dict[str, float]:
    low, high = min(values.values()), max(values.values())
    if math.isclose(low, high):
        return {key: 100.0 for key in values}
    return {
        key: round(
            ((high - value) if lower_is_better else (value - low)) / (high - low) * 100,
            4,
        )
        for key, value in values.items()
    }


def rank_models(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = {row["model"]: row for row in summaries}
    components = {
        "quality": _normalize({m: float(v["quality_mean"]) for m, v in indexed.items()}, False),
        "latency": _normalize({m: float(v["latency_mean_ms"]) for m, v in indexed.items()}, True),
        "token_efficiency": _normalize(
            {m: float(v["total_tokens_avg"]) for m, v in indexed.items()}, True
        ),
        "stability": {m: float(v["stability_success_rate"]) for m, v in indexed.items()},
        "policy_compliance": {m: float(v["policy_compliance_rate"]) for m, v in indexed.items()},
        "format_compliance": {m: float(v["format_compliance_rate"]) for m, v in indexed.items()},
        "consistency": {m: float(v["consistency_mean"]) for m, v in indexed.items()},
    }
    available_weight = sum(WEIGHTS[key] for key in components)
    ranking = []
    for model in MODELS:
        score = sum(WEIGHTS[key] * values[model] for key, values in components.items())
        ranking.append(
            {
                "model": model,
                "weighted_score_available_metrics": round(score / available_weight, 4),
                "fixed_weights": WEIGHTS,
                "available_weight": available_weight,
                "cost_component": None,
                "cost_reason": "N/A_OFFICIAL_PER_MODEL_API_TRIAL_PRICE_NOT_VERIFIED",
                "normalized_components": {key: values[model] for key, values in components.items()},
            }
        )
    return sorted(ranking, key=lambda row: row["weighted_score_available_metrics"], reverse=True)


def sources() -> list[dict[str, str]]:
    return [
        {
            "source_id": "NIST-AI-RMF-1.0",
            "tier": "OFFICIAL_STANDARD",
            "title": "Artificial Intelligence Risk Management Framework (AI RMF 1.0)",
            "date": "2023-01-26",
            "status": "CURRENT_1.0_REVISION_IN_PROGRESS_AS_OF_2026-09-12",
            "url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
            "section": "Sections 3 and 5; MEASURE 1-3",
            "use": (
                "Trustworthiness, context-sensitive measurement, documented TEVV and uncertainty."
            ),
        },
        {
            "source_id": "NIST-AI-600-1",
            "tier": "OFFICIAL_STANDARD",
            "title": "AI RMF: Generative Artificial Intelligence Profile",
            "date": "2024-07-26",
            "status": "FINAL",
            "url": "https://doi.org/10.6028/NIST.AI.600-1",
            "section": "GAI risks and suggested actions across Govern, Map, Measure and Manage",
            "use": (
                "Generative-model evaluation, deployment context, monitoring and risk measurement."
            ),
        },
        {
            "source_id": "NIST-AI-200-2-IPD",
            "tier": "OFFICIAL_DRAFT",
            "title": "TEVV-Athlon Framework for Evaluating AI Systems",
            "date": "2026-08-07",
            "status": "INITIAL_PUBLIC_DRAFT_SUPPORTING_REFERENCE",
            "url": "https://www.nist.gov/artificial-intelligence/ai-research/tevv-athlon-framework-evaluating-ai-systems",
            "section": "Initial Public Draft overview",
            "use": "Use-case-specific, repeatable, extensible and customizable TEVV design.",
        },
        {
            "source_id": "MLPERF-INFERENCE",
            "tier": "OFFICIAL_BENCHMARK",
            "title": "MLPerf Inference Datacenter",
            "date": "2026-09-12",
            "status": "LIVING_BENCHMARK",
            "url": "https://mlcommons.org/benchmarks/inference-datacenter/",
            "section": "Scenarios & Metrics; latency constraints, throughput and compliance",
            "use": "Representative inference measurement and percentile latency.",
        },
        {
            "source_id": "MLPERF-LLM-LATENCY",
            "tier": "OFFICIAL_BENCHMARK",
            "title": "Llama 2 70B: An MLPerf Inference Benchmark for LLMs",
            "date": "2024-03",
            "status": "PUBLISHED",
            "url": "https://mlcommons.org/2024/03/mlperf-llama2-70b/",
            "section": "Latency constraints for the server scenario",
            "use": "TTFT, TPOT/TBT and tokens-per-second terminology.",
        },
        {
            "source_id": "HELM",
            "tier": "PEER_REVIEWED",
            "title": "Holistic Evaluation of Language Models",
            "date": "2023",
            "status": "PUBLISHED",
            "url": "https://arxiv.org/abs/2211.09110",
            "section": "Holistic, reproducible and transparent model evaluation",
            "use": "Multi-metric evaluation and explicit trade-offs rather than one score.",
        },
        {
            "source_id": "CHECKLIST",
            "tier": "PEER_REVIEWED",
            "title": "Beyond Accuracy: Behavioral Testing of NLP Models with CheckList",
            "date": "2020-07",
            "status": "ACL_PUBLISHED",
            "url": "https://aclanthology.org/2020.acl-main.442/",
            "section": "Capability and test-type matrix",
            "use": "Stratified behavioral cases beyond aggregate accuracy.",
        },
        {
            "source_id": "NVIDIA-NIM-API",
            "tier": "PROVIDER_OFFICIAL",
            "title": "NVIDIA NIM for LLMs API Reference",
            "date": "2026-09-10",
            "status": "CURRENT",
            "url": "https://docs.nvidia.com/nim/large-language-models/latest/api-reference.html",
            "section": "OpenAI-compatible chat completions",
            "use": "Provider response and token-usage metadata contract.",
        },
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _winner(summaries: list[dict[str, Any]], field: str, lower: bool = False) -> str:
    eligible = [row for row in summaries if row[field] is not None]
    best_value = (
        min(float(row[field]) for row in eligible)
        if lower
        else max(float(row[field]) for row in eligible)
    )
    return "; ".join(
        str(row["model"])
        for row in eligible
        if math.isclose(float(row[field]), best_value, abs_tol=0.0001)
    )


def analyze(output_dir: Path) -> dict[str, Any]:
    payload = json.loads((output_dir / "benchmark_runs.json").read_text(encoding="utf-8"))
    runs = cast(list[dict[str, Any]], payload["runs"])
    cases = build_cases()
    validate_runs(runs, cases)
    if payload.get("provider_actual_calls") != 270:
        raise BenchmarkError("provider call count does not match the frozen execution count")
    summaries = summarize(runs)
    statistical = statistics_report(runs)
    ranking = rank_models(summaries)
    recommendation = ranking[0]["model"]
    _atomic_json(output_dir / "benchmark_model_summary.json", {"models": summaries})
    _atomic_json(
        output_dir / "benchmark_model_ranking.json",
        {"ranking": ranking, "recommended_model": recommendation},
    )
    _atomic_json(output_dir / "benchmark_sources.json", {"sources": sources()})
    _atomic_json(
        output_dir / "benchmark_validation.json",
        {
            "status": "PASS",
            "expected_executions": 270,
            "actual_executions": len(runs),
            "unique_case_model_repetition_combinations": 270,
            "synthetic_public_data_only": True,
            "production_runtime_invoked": False,
            "production_governance": PRODUCTION_GOVERNANCE,
        },
    )
    metric_fields = [
        "case_id",
        "workload",
        "model",
        "repetition",
        "success",
        "error_type",
        "timeout",
        "latency_ms",
        "ttft_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost",
        "quality_score",
        "policy_compliance",
        "format_compliance",
        "trace_id",
        "response_digest",
    ]
    _write_csv(output_dir / "benchmark_metrics.csv", runs, metric_fields)
    _write_csv(
        output_dir / "benchmark_model_ranking.csv",
        ranking,
        [
            "model",
            "weighted_score_available_metrics",
            "available_weight",
            "cost_component",
            "cost_reason",
        ],
    )
    crosswalk = [
        {
            "metric": "Quality",
            "measurement": "correctness, completeness, groundedness, required information coverage",
            "evidence": "NIST AI RMF Valid & Reliable; NIST AI 600-1; HELM",
            "rationale": "Financial task output reliability",
        },
        {
            "metric": "Latency",
            "measurement": "E2E mean, p50, p95, min, max; TTFT when exposed",
            "evidence": "MLPerf Inference",
            "rationale": "Online inference responsiveness",
        },
        {
            "metric": "Token Efficiency",
            "measurement": "input, output and total tokens",
            "evidence": "NVIDIA NIM API metadata; HELM efficiency",
            "rationale": "Operational resource efficiency",
        },
        {
            "metric": "Cost",
            "measurement": "per-request and quality-adjusted cost when official price exists",
            "evidence": "Provider official pricing",
            "rationale": "Adoption economics without invented prices",
        },
        {
            "metric": "Stability",
            "measurement": "success, error, timeout and malformed-output rates",
            "evidence": "NIST AI RMF Valid & Reliable; TEVV-Athlon draft",
            "rationale": "Operational reliability",
        },
        {
            "metric": "Policy Compliance",
            "measurement": "field allowlist, TOKEN/HMAC, REQUIRED_EXACT and forbidden disclosure",
            "evidence": "NIST Measure/Manage plus frozen FPG controls",
            "rationale": "Model-behavior compliance, separate from production provider approval",
        },
        {
            "metric": "Format Compliance",
            "measurement": "JSON parse, exact schema, required fields and types",
            "evidence": "TEVV verification; CheckList",
            "rationale": "System integration fitness",
        },
        {
            "metric": "Consistency",
            "measurement": "three-run answer agreement and contract consistency",
            "evidence": "NIST reliability; TEVV-Athlon draft",
            "rationale": "Repeated-run reliability",
        },
    ]
    _write_csv(
        output_dir / "benchmark_metric_crosswalk.csv",
        crosswalk,
        ["metric", "measurement", "evidence", "rationale"],
    )
    evidence_doc = "\n".join(
        [
            "# Benchmark Metric Evidence",
            "",
            "## Evaluation Framework",
            "",
            (
                "This is a NIST AI RMF / TEVV-aligned operational evaluation, not a "
                "generic model leaderboard or independent conformity assessment. The eight metrics "
                "were operationalized by FPG; no source is represented as prescribing this "
                "exact set."
            ),
            "",
            "## NIST AI RMF",
            "",
            (
                "AI RMF 1.0 (2023-01-26) supplies the Valid & Reliable, Safe, Secure & "
                "Resilient, Accountable & Transparent characteristics and the "
                "GOVERN/MAP/MEASURE/MANAGE structure. MEASURE calls for appropriate metrics, "
                "repeatable TEVV, uncertainty, benchmark comparison and documented results. "
                "NIST states that AI RMF 1.0 is under revision as of 2026-09-12, so this "
                "benchmark records 1.0 as its versioned basis rather than anticipating the "
                "revision."
            ),
            "",
            "## NIST Generative AI Profile",
            "",
            (
                "NIST AI 600-1 (2024-07-26, final) is the cross-sector companion profile "
                "used for generative-model risk measurement, deployment-context analysis "
                "and monitoring."
            ),
            "",
            "## NIST TEVV-Athlon",
            "",
            (
                "NIST AI 200-2 was an Initial Public Draft announced 2026-08-07 with "
                "comments open through 2026-10-06. It is only a supporting reference. Its "
                "extensible, adaptable and use-case-specific evaluation framing informs "
                "the repeated synthetic case design."
            ),
            "",
            "## MLPerf / MLCommons",
            "",
            (
                "MLPerf supplies industry terminology for end-to-end latency, percentiles, "
                "TTFT, TPOT/TBT and tokens per second. This harness is not an MLPerf "
                "submission; non-streaming provider calls expose E2E latency and token "
                "usage, while TTFT remains N/A."
            ),
            "",
            "## Peer-reviewed references",
            "",
            (
                "HELM motivates transparent multi-metric evaluation and trade-off "
                "reporting. CheckList motivates stratified capability-oriented behavioral "
                "cases beyond one aggregate accuracy measure."
            ),
            "",
            "## 8-Metric Crosswalk",
            "",
            "See `benchmark_metric_crosswalk.csv`.",
            "",
            "## Limitations",
            "",
            "- NIST does not prescribe these exact eight metrics.",
            (
                "- The metrics operationalize NIST principles for this frozen FPG "
                "financial workload."
            ),
            (
                "- Token and cost are operational-efficiency measures; cost is N/A without "
                "verified official per-model API Trial prices."
            ),
            (
                "- Policy Compliance measures model behavior against field/output "
                "constraints, not Production E2 provider authorization."
            ),
            "- TEVV-Athlon is an Initial Public Draft, not a final standard.",
            "- Provider non-streaming metadata does not expose TTFT or TPOT.",
            ("- The 30 cases are model-selection data and must not be reused as hold-out data."),
            "",
        ]
    )
    (output_dir / "benchmark_metric_evidence.md").write_text(evidence_doc, encoding="utf-8")
    winners = {
        "quality": _winner(summaries, "quality_mean"),
        "latency": _winner(summaries, "latency_mean_ms", True),
        "token": _winner(summaries, "total_tokens_avg", True),
        "cost": "N/A",
        "stability": _winner(summaries, "stability_success_rate"),
        "policy": _winner(summaries, "policy_compliance_rate"),
        "format": _winner(summaries, "format_compliance_rate"),
        "consistency": _winner(summaries, "consistency_mean"),
    }
    report = _report_markdown(summaries, statistical, ranking, winners, recommendation)
    (output_dir / "benchmark_report.md").write_text(report, encoding="utf-8")
    ppt = _ppt_markdown(summaries, ranking, winners, recommendation)
    (output_dir / "benchmark_ppt_summary.md").write_text(ppt, encoding="utf-8")
    return {
        "summaries": summaries,
        "statistics": statistical,
        "ranking": ranking,
        "winners": winners,
        "recommended_model": recommendation,
    }


def _report_markdown(
    summaries: list[dict[str, Any]],
    statistical: list[dict[str, Any]],
    ranking: list[dict[str, Any]],
    winners: dict[str, str],
    recommendation: str,
) -> str:
    recommendation_margin = round(
        ranking[0]["weighted_score_available_metrics"]
        - ranking[1]["weighted_score_available_metrics"],
        4,
    )
    lines = [
        "# Three-Model Isolated Operational Benchmark",
        "",
        "## 1. Purpose",
        "",
        (
            "Compare three models under identical synthetic financial tasks while "
            "preserving the frozen Production E1/E2/E3 baseline."
        ),
        "",
        "## 2. Evidence Basis",
        "",
        (
            "This NIST AI RMF / TEVV-aligned operational evaluation uses NIST AI RMF 1.0 "
            "and NIST AI 600-1 to ground trustworthiness and GAI "
            "measurement; the NIST AI 200-2 TEVV-Athlon Initial Public Draft is a "
            "supporting design reference; MLPerf supplies inference terminology. This is "
            "not an independent conformity assessment or an MLPerf result."
        ),
        "",
        "## 3. Design",
        "",
        (
            "30 cases × 6 workload strata × 3 models × 3 repetitions = 270 actual model "
            "executions. Inputs are synthetic and non-linkable. Temperature 0, top_p 1, "
            "512 output tokens and JSON output are fixed."
        ),
        "",
        "## 4. Metrics",
        "",
        (
            "Quality, Latency, Token Efficiency, Cost, Stability, Policy Compliance, "
            "Format Compliance and Consistency are frozen before execution. Cost is N/A "
            "without verified official per-model API Trial pricing."
        ),
        "",
        "## 5. Results",
        "",
        (
            "| Model | Quality | Latency mean ms | p95 ms | Tokens avg | Stability % | "
            "Policy % | Format % | Consistency |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['model']} | {row['quality_mean']} | "
            f"{row['latency_mean_ms']} | {row['latency_p95_ms']} | "
            f"{row['total_tokens_avg']} | {row['stability_success_rate']} | "
            f"{row['policy_compliance_rate']} | {row['format_compliance_rate']} | "
            f"{row['consistency_mean']} |"
        )
    lines.extend(
        [
            "",
            "### Workload Quality",
            "",
            "| Model | Workload | Quality mean |",
            "|---|---|---:|",
        ]
    )
    for row in summaries:
        for workload, quality in row["quality_by_workload"].items():
            lines.append(f"| {row['model']} | {workload} | {quality} |")
    lines.extend(
        [
            "",
            "## 6. Statistical Comparison",
            "",
            (
                "Paired Friedman tests use case × repetition blocks; Kendall's W is "
                "reported as the omnibus effect size."
            ),
            "",
            "| Metric | Blocks | Statistic | p-value | Kendall W |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in statistical:
        lines.append(
            f"| {row['metric']} | {row['blocks']} | {row['statistic']} | "
            f"{row['p_value']} | {row['effect_value']} |"
        )
    lines.extend(
        [
            "",
            "## 7. Trade-offs",
            "",
            *[f"- {key}: {value}" for key, value in winners.items()],
            "",
            (
                "The comparison retains raw metrics; it does not claim that one model "
                "dominates every dimension."
            ),
            "",
            "## 8. Recommended Model",
            "",
            (
                f"**{recommendation}** has the highest pre-frozen weighted score over "
                "available metrics "
                f"({ranking[0]['weighted_score_available_metrics']}). The cost component "
                "remains N/A and is excluded from the calculable 90% denominator; fixed "
                "weights were not changed."
            ),
            (
                f"The margin over the second available-metric score is "
                f"{recommendation_margin} "
                "points, so the recommendation is provisional until a new hold-out confirms it."
            ),
            (
                "For each calculable metric, min-max normalization maps the observed "
                "three-model range to 0-100; lower is better for latency and tokens. "
                "The available fixed weights are then renormalized over 90%."
            ),
            "",
            "## 9. FPG Meaning",
            "",
            "### Production Runtime",
            "",
            "`ACTIVE_FAIL_CLOSED / BLOCK`",
            "",
            "### Model Evaluation",
            "",
            "`ISOLATED BENCHMARK HARNESS`",
            "",
            "> Benchmark actual calls do not authorize Production External Execution.",
            "",
            (
                "FPG remains model-independent: it compares model behavior under common "
                "field, exactness and output constraints without altering Production "
                "E1/E2/E3."
            ),
            "",
            "## 10. Next",
            "",
            (
                "Freeze this benchmark/evidence, create a new non-overlapping hold-out "
                "dataset, and validate only the selected model."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _ppt_markdown(
    summaries: list[dict[str, Any]],
    ranking: list[dict[str, Any]],
    winners: dict[str, str],
    recommendation: str,
) -> str:
    lines = [
        "# 금융 AI 운영 적합성 검증",
        "",
        "## 근거",
        "",
        (
            "NIST AI RMF / TEVV-aligned operational evaluation. NIST AI 600-1 기반 + "
            "NIST AI 200-2 Initial Public Draft 참고 + MLPerf inference metrics. 독립 "
            "적합성 평가 또는 MLPerf 결과가 아니다."
        ),
        "",
        "## 실험",
        "",
        "- 30 Cases × 3 Models × 3 Runs = 270 Executions",
        "- 6 Workload Groups",
        "- 8 Operational Metrics",
        "- Synthetic/non-linkable data only",
        "",
        "## 모델별 핵심 결과",
        "",
        "| Model | Quality | Mean latency | Tokens | Stability | Compliance | Consistency |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['model']} | {row['quality_mean']} | "
            f"{row['latency_mean_ms']} ms | {row['total_tokens_avg']} | "
            f"{row['stability_success_rate']}% | {row['policy_compliance_rate']}% | "
            f"{row['consistency_mean']} |"
        )
    lines.extend(
        [
            "",
            "## Trade-off winners",
            "",
            *[f"- {key}: {value}" for key, value in winners.items()],
            "",
            "## 결론",
            "",
            f"- 추천 모델: **{recommendation}**",
            (
                "- Available-metric weighted score: "
                f"**{ranking[0]['weighted_score_available_metrics']}**"
            ),
            "- Cost는 공식 per-model API Trial 가격 미확인으로 N/A이며 임의 계산하지 않았다.",
            "- Production Runtime은 `ACTIVE_FAIL_CLOSED / BLOCK`을 유지한다.",
            "- Benchmark 실제 호출은 Production External Execution 승인을 의미하지 않는다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "run", "analyze"))
    parser.add_argument("--output-dir", type=Path, default=Path("02_ai/benchmark"))
    parser.add_argument("--workers", type=int, default=9)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output_dir)
    elif args.command == "run":
        runs = run(args.output_dir, workers=args.workers)
        analyze(args.output_dir)
        print(json.dumps({"actual_executions": len(runs)}, sort_keys=True))
    else:
        analyze(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
