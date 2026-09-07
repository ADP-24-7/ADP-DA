"""One execution per row, retaining the producer's actual field names."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from adp_da.bundle_validator import validate_bundle


def execution_dataframe(bundle: dict[str, Any]) -> pd.DataFrame:
    validate_bundle(bundle)
    metrics = {row["execution_id"]: row for row in bundle["runtime_metrics"]}
    traces = {row["execution_id"]: row for row in bundle["trace_index"]}
    config = bundle["execution_config"]
    models = {row["profile_id"]: row for row in config["models"]}
    common = {key: value for key, value in config.items() if key != "models"}
    manifest = bundle["manifest"]
    common.update(
        {
            key: manifest[key]
            for key in (
                "bundle_id",
                "content_digest",
                "generated_at",
                "execution_from",
                "execution_cutoff_at",
            )
        }
    )
    rows = [
        {
            **common,
            **result,
            **metrics[result["execution_id"]],
            **traces[result["execution_id"]],
            **models[result["model_profile_id"]],
        }
        for result in bundle["case_results"]
    ]
    frame = pd.json_normalize(rows, sep=".")
    for column in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "provider_http_status",
        "full_response_latency_millis",
        "attempt_elapsed_millis",
        "initial_runtime_latency_millis",
    ):
        frame[column] = pd.array([row[column] for row in rows], dtype="Int64")
    return frame


def save_dataset(frame: pd.DataFrame, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        path = output_dir / "executions.parquet"
        frame.to_parquet(path, index=False)
        return {"path": str(path), "format": "parquet"}
    except ImportError:
        path = output_dir / "executions.jsonl"
        frame.to_json(path, orient="records", lines=True, force_ascii=False)
        return {
            "path": str(path),
            "format": "jsonl",
            "reason": "Parquet engine unavailable; install the notebook extra.",
        }
