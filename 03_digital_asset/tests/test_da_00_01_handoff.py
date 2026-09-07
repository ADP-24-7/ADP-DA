from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "03_digital_asset/src/build_da_00_01_handoff.py"


@pytest.fixture(scope="module")
def builder() -> Any:
    spec = importlib.util.spec_from_file_location("da_00_01_handoff", BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def artifacts(builder: Any) -> dict[Path, dict[str, Any]]:
    first = ROOT / "03_digital_asset/artifacts/da_00_master_sample/analysis_summary.json"
    generated_at = json.loads(first.read_text(encoding="utf-8"))["generated_at"]
    return builder.build_artifacts(generated_at)


@pytest.mark.parametrize(
    "folder,name",
    [
        ("da_00_master_sample", "analysis_summary"),
        ("da_00_master_sample", "sampling_contract"),
        ("da_00_master_sample", "data_provenance"),
        ("da_01_external_execution", "analysis_summary"),
        ("da_01_external_execution", "statistical_validation"),
        ("da_01_external_execution", "runtime_requirements"),
    ],
)
def test_frozen_artifact_matches_original_evidence(
    artifacts: dict[Path, dict[str, Any]],
    folder: str,
    name: str,
) -> None:
    path = Path("03_digital_asset/artifacts") / folder / (name + ".json")
    assert json.loads((ROOT / path).read_text(encoding="utf-8")) == artifacts[path]


def test_runtime_boundary_and_semantic_not_enum_contract(
    artifacts: dict[Path, dict[str, Any]],
) -> None:
    path = Path("03_digital_asset/artifacts/da_01_external_execution/runtime_requirements.json")
    result = artifacts[path]["result"]
    assert result["new_runtime_enums"] == []
    assert result["new_runtime_fields"] == []
    assert result["new_active_runtime_controls"] == []
    assert {"KYC", "AML", "Sanctions", "Wallet Risk", "VASP Risk", "Customer Risk Score"}.issubset(
        result["out_of_scope"]
    )
    assert result["requirement"] == "SUBMITTED / SENT != EXECUTION_CONFIRMED"


def test_recorded_posthoc_rounding_is_not_claimed_as_exact_zero(
    artifacts: dict[Path, dict[str, Any]],
) -> None:
    path = Path("03_digital_asset/artifacts/da_01_external_execution/statistical_validation.json")
    artifact = artifacts[path]
    pairs = artifact["metrics"]["posthoc_comparisons"]
    assert len({row["comparison"] for row in pairs}) == 10
    assert sum(row["significant"] for row in pairs) == 7
    assert all(isinstance(row["p_value_display"], str) for row in pairs)
    assert artifact["metrics"]["p_value_reported"] > 0


@pytest.fixture()
def copied_evidence(builder: Any, tmp_path: Path) -> Path:
    for relative in (
        builder.NB0,
        builder.NB1,
        builder.DATA,
        builder.DOC0,
        builder.DOC1,
        builder.GAPS,
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_duplicate_csv_row_is_rejected(builder: Any, copied_evidence: Path) -> None:
    path = copied_evidence / builder.DATA
    with path.open("rb") as file:
        file.readline()
        row = file.readline()
    with path.open("ab") as file:
        file.write(row)
    with pytest.raises(ValueError, match="allocation mismatch"):
        builder.verify_sources(copied_evidence)


def test_changed_recorded_statistic_is_rejected(builder: Any, copied_evidence: Path) -> None:
    path = copied_evidence / builder.NB1
    original = path.read_text(encoding="utf-8")
    assert "672.6848" in original
    path.write_text(original.replace("672.6848", "673.6848"), encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        builder.verify_sources(copied_evidence)


def test_local_handoff_links_resolve() -> None:
    for path in (ROOT / "03_digital_asset/docs/handoff").glob("*.md"):
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "#")):
                assert (path.parent / link.split("#")[0]).exists(), (path, link)


def test_foundation_builder_references_resolve() -> None:
    for path in (ROOT / "03_digital_asset/src").glob("build_*.py"):
        source = path.read_text(encoding="utf-8")
        match = re.search(r'NOTEBOOK = DA / "notebooks" / "foundation" / "([^"]+)"', source)
        if match:
            assert (ROOT / "03_digital_asset/notebooks/foundation" / match[1]).is_file()
        assert not re.search(r'NOTEBOOK = DA / "notebooks" / "0[1-5]_', source)
