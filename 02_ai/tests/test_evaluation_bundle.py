from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from adp_da.bundle_analysis import analyze_bundle, paired_test
from adp_da.bundle_dataset import execution_dataframe
from adp_da.bundle_loader import load_bundle
from adp_da.bundle_validator import (
    BundleValidationError,
    canonical_json,
    content_digest,
    validate_bundle,
)
from adp_da.evaluation_bundle import run_pipeline
from bundle_fixture_factory import make_bundle


def test_valid_contract_and_dataframe() -> None:
    bundle = make_bundle()
    report = validate_bundle(bundle)
    assert report["execution_count"] == 16
    frame = execution_dataframe(bundle)
    assert len(frame) == frame.execution_id.nunique() == 16
    assert "workload_id" not in frame
    assert "utility" not in frame
    assert str(frame.input_tokens.dtype) == "Int64"
    assert frame.total_tokens.isna().any()


def test_stored_fixture_digest_and_schema_parity() -> None:
    fixture = Path(__file__).parent / "fixtures/evaluation_bundle.synthetic.json"
    report = validate_bundle(json.loads(fixture.read_text(encoding="utf-8")))
    assert report["calculated_digest"] == (
        "sha256:ed159d36cd3f7bfa47d0f05b4cd4334b9b2a09c15af14128b9baff6f5036501b"
    )
    root = Path(__file__).resolve().parents[2]
    producer = root.parent / "ADP-BE/docs/contracts/ai-evaluation-bundle.schema.json"
    if producer.exists():
        consumer = root / "02_ai/contracts/ai-evaluation-bundle.schema.json"
        assert consumer.read_bytes() == producer.read_bytes()


def test_large_token_integer_survives_nullable_dataframe(tmp_path: Path) -> None:
    from adp_da.bundle_dataset import save_dataset

    bundle = make_bundle()
    metric = bundle["runtime_metrics"][1]
    metric["input_tokens"] = 2**53 + 1
    metric["total_tokens"] = metric["input_tokens"] + metric["output_tokens"]
    bundle["manifest"]["content_digest"] = content_digest(bundle)
    frame = execution_dataframe(bundle)
    assert frame.loc[1, "input_tokens"] == 2**53 + 1
    pytest.importorskip("pyarrow")
    dataset = save_dataset(frame, tmp_path)
    restored = pd.read_parquet(dataset["path"])
    assert restored.loc[1, "input_tokens"] == 2**53 + 1
    assert pd.isna(restored.loc[0, "input_tokens"])


def test_api_success_preserves_bytes_without_credential_metadata(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from io import BytesIO

    from adp_da import bundle_loader

    raw = json.dumps(make_bundle()).encode()

    class FakeOpener:
        def open(self, request: Any, timeout: float) -> BytesIO:
            return BytesIO(raw)

    monkeypatch.setattr(bundle_loader, "build_opener", lambda _: FakeOpener())
    _, metadata = load_bundle(
        "https://example.invalid",
        tmp_path,
        evaluation_run_id="SYNTHETIC-DA-CONSUMER-TEST",
        token="never-archive-this",
    )
    assert Path(metadata["raw_path"]).read_bytes() == raw
    assert "never-archive-this" not in json.dumps(metadata)
    assert metadata["source_type"] == "api"


def test_api_supports_local_admin_headers_without_archiving_values(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from io import BytesIO

    from adp_da import bundle_loader

    raw = json.dumps(make_bundle()).encode()

    class FakeOpener:
        def open(self, request: Any, timeout: float) -> BytesIO:
            assert request.get_header("Authorization") is None
            assert request.get_header("X-adp-user-id") == "da-evaluation-reader"
            assert request.get_header("X-adp-user-roles") == "PRIVILEGED_OPERATOR"
            return BytesIO(raw)

    monkeypatch.setattr(bundle_loader, "build_opener", lambda _: FakeOpener())
    _, metadata = load_bundle(
        "https://example.invalid",
        tmp_path,
        evaluation_run_id="SYNTHETIC-DA-CONSUMER-TEST",
        local_admin_user_id="da-evaluation-reader",
        local_admin_roles="PRIVILEGED_OPERATOR",
    )
    serialized_metadata = json.dumps(metadata)
    assert "da-evaluation-reader" not in serialized_metadata
    assert "PRIVILEGED_OPERATOR" not in serialized_metadata


@pytest.mark.parametrize(
    ("credentials", "message"),
    [
        ({"local_admin_user_id": "reader"}, "provided together"),
        ({"local_admin_roles": "PRIVILEGED_OPERATOR"}, "provided together"),
        (
            {
                "token": "bearer",
                "local_admin_user_id": "reader",
                "local_admin_roles": "PRIVILEGED_OPERATOR",
            },
            "mutually exclusive",
        ),
        ({"token": "unsafe\nvalue"}, "line breaks"),
        (
            {
                "local_admin_user_id": "reader\r\nInjected: value",
                "local_admin_roles": "PRIVILEGED_OPERATOR",
            },
            "line breaks",
        ),
    ],
)
def test_api_rejects_ambiguous_or_unsafe_authentication(
    tmp_path: Path, credentials: dict[str, str], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        load_bundle(
            "https://example.invalid",
            tmp_path,
            evaluation_run_id="run",
            **credentials,
        )


def test_cli_reads_local_admin_authentication_from_named_environment_variables(
    tmp_path: Path, monkeypatch: Any
) -> None:
    import sys

    from adp_da import evaluation_bundle

    captured: dict[str, Any] = {}

    def fake_run_pipeline(source: str, output: Path, **options: Any) -> Path:
        captured.update({"source": source, "output": output, **options})
        return tmp_path / "analysis"

    monkeypatch.delenv("ADP_BE_TOKEN", raising=False)
    monkeypatch.setenv("TEST_ADMIN_USER", "da-evaluation-reader")
    monkeypatch.setenv("TEST_ADMIN_ROLES", "PRIVILEGED_OPERATOR")
    monkeypatch.setattr(evaluation_bundle, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "evaluation_bundle",
            "http://localhost:8080",
            "--output",
            str(tmp_path / "output"),
            "--evaluation-run-id",
            "run-1",
            "--local-admin-user-id-env",
            "TEST_ADMIN_USER",
            "--local-admin-roles-env",
            "TEST_ADMIN_ROLES",
        ],
    )

    evaluation_bundle.main()

    assert captured["token"] is None
    assert captured["local_admin_user_id"] == "da-evaluation-reader"
    assert captured["local_admin_roles"] == "PRIVILEGED_OPERATOR"


def test_invalid_bundle_never_creates_analysis_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "invalid.json"
    source.write_text('{"value": NaN}')
    with pytest.raises(BundleValidationError):
        run_pipeline(source, tmp_path / "out")
    assert not list((tmp_path / "out").rglob("evaluation_summary.json"))


@pytest.mark.parametrize(
    "mutation",
    [
        "schema",
        "digest",
        "execution_set",
        "relationship",
        "duplicate_pair",
        "cartesian",
        "count",
        "input",
        "cross_model_input",
        "failure",
        "token_sum",
        "token_status",
        "evidence",
        "measurement",
        "latency",
        "run",
        "model_duplicate",
        "provider",
        "timestamp",
        "window",
        "raw_private_field",
        "duplicate_metric",
        "duplicate_trace",
    ],
)
def test_corruption_fails_closed_even_with_recomputed_digest(mutation: str) -> None:
    bundle = make_bundle()
    result, metric = bundle["case_results"][0], bundle["runtime_metrics"][0]
    if mutation == "schema":
        del result["runtime_status"]
    elif mutation == "digest":
        metric["initial_runtime_latency_millis"] += 1
    elif mutation == "execution_set":
        bundle["trace_index"][0]["execution_id"] = "unknown"
    elif mutation == "relationship":
        metric["eval_case_id"] = "wrong-case"
    elif mutation == "duplicate_pair":
        for section in ("case_results", "runtime_metrics"):
            bundle[section][1]["model_profile_id"] = bundle[section][0]["model_profile_id"]
    elif mutation == "cartesian":
        for section in ("case_results", "runtime_metrics", "trace_index"):
            bundle[section].pop()
        bundle["manifest"]["execution_count"] -= 1
    elif mutation == "count":
        bundle["manifest"]["case_count"] += 1
    elif mutation == "input":
        result["actual_input_digest"] = "b" * 64
    elif mutation == "cross_model_input":
        result["expected_input_digest"] = result["actual_input_digest"] = "b" * 64
    elif mutation == "failure":
        bundle["failure_summary"]["failed"] += 1
    elif mutation == "token_sum":
        bundle["runtime_metrics"][1]["total_tokens"] += 1
    elif mutation == "token_status":
        metric["total_tokens"] = 0
    elif mutation == "evidence":
        result["evidence_status"] = "PARTIAL"
    elif mutation == "measurement":
        metric["measurement_type"] = "TIMEOUT"
    elif mutation == "latency":
        metric["attempt_elapsed_millis"] = 1
    elif mutation == "run":
        bundle["manifest"]["evaluation_run_id"] = "different"
    elif mutation == "model_duplicate":
        bundle["execution_config"]["models"].append(bundle["execution_config"]["models"][0])
    elif mutation == "provider":
        result["provider_status"] = "ACKNOWLEDGED"
    elif mutation == "timestamp":
        bundle["trace_index"][0]["created_at"] = "not-a-timestamp"
    elif mutation == "window":
        bundle["manifest"]["execution_from"] = "2020-01-01T00:00:00Z"
    elif mutation == "raw_private_field":
        result["prompt"] = "must not be analyzed"
    elif mutation == "duplicate_metric":
        bundle["runtime_metrics"][1] = copy.deepcopy(metric)
    elif mutation == "duplicate_trace":
        bundle["trace_index"][1] = copy.deepcopy(bundle["trace_index"][0])
    if mutation != "digest":
        bundle["manifest"]["content_digest"] = content_digest(bundle)
    with pytest.raises(BundleValidationError):
        validate_bundle(bundle)


def test_digest_excludes_manifest_but_keeps_array_order_and_null() -> None:
    bundle = make_bundle()
    expected = content_digest(bundle)
    bundle["manifest"]["generated_at"] = "2027-01-01T00:00:00Z"
    assert content_digest(bundle) == expected
    reversed_keys = dict(reversed(list(bundle.items())))
    assert content_digest(reversed_keys) == expected
    bundle["case_results"].reverse()
    assert content_digest(bundle) != expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0.0"),
        (-0.0, "-0.0"),
        (0.001, "0.001"),
        (0.0001, "1.0E-4"),
        (1e7, "1.0E7"),
        (1e-7, "1.0E-7"),
        (1.25e9, "1.25E9"),
        (0.7, "0.7"),
    ],
)
def test_java_number_notation(value: float, expected: str) -> None:
    assert canonical_json(value) == expected


def test_raw_snapshot_preservation_and_failure_archive(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    bundle = make_bundle()
    raw = json.dumps(bundle, indent=3).encode()
    source.write_bytes(raw)
    _, metadata = load_bundle(source, tmp_path / "raw")
    assert Path(metadata["raw_path"]).read_bytes() == raw
    bundle["manifest"]["generated_at"] = "2026-09-02T00:00:00Z"
    source.write_text(json.dumps(bundle))
    _, second = load_bundle(source, tmp_path / "raw")
    assert metadata["content_digest"] == second["content_digest"]
    assert metadata["raw_path"] != second["raw_path"]
    source.write_text('{"manifest": {}, "manifest": {}}')
    with pytest.raises(BundleValidationError, match="duplicate"):
        load_bundle(source, tmp_path / "rejected")
    assert len(list((tmp_path / "rejected").glob("*.json"))) == 1


def test_pipeline_artifacts_and_no_policy_promotion(tmp_path: Path) -> None:
    source = tmp_path / "fixture.json"
    source.write_text(json.dumps(make_bundle()))
    output = run_pipeline(source, tmp_path / "output", synthetic=True)
    expected = {
        "evaluation_summary.json",
        "model_comparison.json",
        "runtime_analysis.json",
        "failure_analysis.json",
        "policy_effect_analysis.json",
        "AI_EVALUATION_DA_REPORT.md",
    }
    assert expected.issubset({path.name for path in output.iterdir()})
    summary = json.loads((output / "evaluation_summary.json").read_text())
    assert summary["data_origin"] == "SYNTHETIC_FIXTURE"
    assert all(row["candidate_value"] is None for row in summary["decision_candidates"])
    assert all(row["status"] != "SUPPORTED_CANDIDATE" for row in summary["decision_candidates"])
    with pytest.raises(FileExistsError):
        run_pipeline(source, tmp_path / "output", synthetic=True)


def test_no_assumptions_no_test_and_mock_excluded() -> None:
    artifacts = analyze_bundle(execution_dataframe(make_bundle()), synthetic=True)
    assert artifacts["model_comparison"]["paired_test"]["p_value"] is None
    runtime = artifacts["runtime_analysis"]["paired_test"]
    assert runtime["sample_size"] == 5  # 8 cases minus attempt/not-attempted/mock
    assert artifacts["policy_effect_analysis"]["status"] == "NOT_EVALUABLE"


def paired_frame(values: list[list[float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"eval_case_id": str(i), "model_profile_id": str(j), "value": value}
            for i, row in enumerate(values)
            for j, value in enumerate(row)
        ]
    )


def test_exact_mcnemar_known_discordances() -> None:
    frame = paired_frame([[1, 0]] * 6 + [[0, 0]] * 2)
    result = paired_test(
        frame,
        "value",
        {},
        binary=True,
        independent_cases=True,
        symmetric_differences=False,
        synthetic=True,
    )
    assert result["p_value"] == pytest.approx(0.03125)
    assert result["effect_size"]["value"] == 0.75


def test_wilcoxon_effect_and_degenerate_cases() -> None:
    options: dict[str, Any] = {
        "binary": False,
        "independent_cases": True,
        "symmetric_differences": True,
        "synthetic": True,
    }
    result = paired_test(paired_frame([[i + 1, 0] for i in range(6)]), "value", {}, **options)
    assert result["p_value"] == pytest.approx(0.03125)
    assert result["effect_size"]["value"] == 1
    tied = paired_test(paired_frame([[1, 1]] * 10), "value", {}, **options)
    assert tied["p_value"] is None


def test_cochran_and_friedman_branches() -> None:
    options = {"independent_cases": True, "symmetric_differences": False, "synthetic": True}
    cochran = paired_test(paired_frame([[1, 0, 0]] * 24), "value", {}, binary=True, **options)
    assert cochran["test_statistic"] == 48
    assert cochran["effect_size"]["value"] == 1
    values = np.tile(np.arange(7), (12, 1)).tolist()
    friedman = paired_test(paired_frame(values), "value", {}, binary=False, **options)
    assert friedman["effect_size"]["value"] == pytest.approx(1)


def test_api_run_binding_and_no_credential_redirect(tmp_path: Path, monkeypatch: Any) -> None:
    from io import BytesIO

    from adp_da import bundle_loader

    class FakeOpener:
        def open(self, request: Any, timeout: float) -> BytesIO:
            assert request.full_url.endswith("/evaluation-runs/wrong%2Frun/bundle")
            assert request.get_header("Authorization") == "Bearer ephemeral"
            return BytesIO(json.dumps(make_bundle()).encode())

    monkeypatch.setattr(bundle_loader, "build_opener", lambda _: FakeOpener())
    with pytest.raises(BundleValidationError, match="requested evaluation run"):
        load_bundle(
            "https://example.invalid", tmp_path, evaluation_run_id="wrong/run", token="ephemeral"
        )
    with pytest.raises(ValueError, match="HTTPS"):
        load_bundle("http://example.invalid", tmp_path, evaluation_run_id="run")
