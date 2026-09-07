from __future__ import annotations

import copy
import importlib
import json
import re
import sys
from pathlib import Path

import jsonschema
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "03_digital_asset/src"))
da04 = importlib.import_module("da_04_outbound_destination")
nb_builder = importlib.import_module("build_da_04_notebook")


@pytest.fixture(scope="module")
def result():
    return da04.analyze()


def test_artifacts_reproduce_and_validate_schema(result):
    da04.export_artifacts(result, check=True)
    schema = da04.read_json(ROOT / da04.DA / "contracts/da_04_evidence.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    for path in (ROOT / da04.ARTIFACT).glob("*.json"):
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
            da04.read_json(path)
        )


def test_notebook_run_all_output_and_markdown_match(result):
    nb = da04.read_json(ROOT / da04.NOTEBOOK)
    assert nb["cells"][0]["cell_type"] == nb["cells"][-1]["cell_type"] == "markdown"
    assert "".join(nb["cells"][-1]["source"]) == nb_builder.final_summary(result)
    outputs = []
    for cell in nb["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is not None
        for output in cell.get("outputs", []):
            assert output["output_type"] != "error"
            outputs.append("".join(output.get("text", [])))
    text = "\n".join(outputs)
    line = next(line for line in text.splitlines() if line.startswith("DA04_RESULT_JSON="))
    assert json.loads(line.split("=", 1)[1]) == result


def test_sample_mapping_does_not_invent_pre_execution_or_identity_values(result):
    fields = {f["required_field"]: f for f in result["field_availability"]}
    for field in [
        "transaction_id",
        "asset",
        "execution_status",
        "originator_identity",
        "beneficiary_identity",
        "kyc_status",
        "counterparty_vasp",
    ]:
        assert fields[field]["sample_column"] is None
        assert fields[field]["sample_value_count"] is None
    assert fields["amount"]["sample_column"] == "value_lossless"
    assert not any(f["pre_execution_approval_verified"] for f in fields.values())
    master = pd.read_csv(ROOT / da04.MASTER, dtype=str, keep_default_na=False)
    assert fields["beneficiary_address"]["sample_value_count"] == int(
        master.to_address.ne("").sum()
    )
    assert result["summary"]["sample_rows"] == len(master)


def test_baseline_and_partition_are_contract_derived(result):
    matrix = da04.read_json(ROOT / da04.MATRIX)
    external = da04.EXTERNAL_DESTINATIONS
    superset = {
        field
        for r in matrix["requirements"]
        for field in r["required_fields"]
        if r["required_exact"] != "INTERNAL_ONLY"
        and any(
            d in external and t != "OMIT" for d, t in r["outbound_transform_by_destination"].items()
        )
    }
    assert set(result["summary"]["externalizable_superset"]) == superset
    for p in result["destination_profiles"]:
        if p["destination"] in external:
            expected = {
                f
                for r in matrix["requirements"]
                for f in r["required_fields"]
                if p["destination"] in r["destination"]
                and r["source_phase"] == p["runtime_phase"]
                and r["outbound_transform_by_destination"][p["destination"]] != "OMIT"
            }
            assert set(p["allowed_fields"]) == expected
            assert not set(p["allowed_fields"]) & set(p["internal_only_fields"])
    for metric in result["exposure"]:
        assert (
            metric["absolute_field_reduction"]
            == len(superset) - metric["destination_payload_field_count"]
        )
        assert metric["unnecessary_external_field_count_in_profile"] == 0


def test_negative_controls_and_normal_contract(result):
    assert not result["contract_violations"]
    assert all(case["detected_as_expected"] for case in result["negative_controls"])
    assert all(case["evidence_type"] == "SIMULATION" for case in result["negative_controls"])
    assert result["invariants"]["pass_through_internal_only_destination_rows"] > 0
    unsupported = next(
        c for c in result["negative_controls"] if c["case"] == "E_UNSUPPORTED_DESTINATION"
    )
    assert unsupported["decision"] == "BLOCK"


@pytest.mark.parametrize(
    "destination,phase",
    [
        ("UNKNOWN", "PRE_EXECUTION"),
        ("BLOCKCHAIN_EXECUTION_SYSTEM", "POST_EXECUTION"),
    ],
)
@pytest.mark.parametrize("fixture", [False, True])
def test_unknown_or_disallowed_destination_phase_blocks(result, destination, phase, fixture):
    frame = pd.DataFrame(result["normalized_requirements"])
    outcome = da04.validate_payload(frame, destination, phase, {}, {}, fixture=fixture)
    assert outcome["decision"] == "BLOCK"
    assert outcome["issues"] == [{"rule": "UNSUPPORTED_DESTINATION_OR_PHASE", "action": "BLOCK"}]


@pytest.mark.parametrize("destination", sorted(da04.EXTERNAL_DESTINATIONS))
def test_every_required_field_missing_is_not_pass(result, destination):
    frame = pd.DataFrame(result["normalized_requirements"])
    p = next(p for p in result["destination_profiles"] if p["destination"] == destination)
    source = {field: "SIMULATION" for field in p["required_fields"]}
    if "amount" in source:
        source["amount"] = "9007199254740993"
    assert (
        da04.validate_payload(frame, destination, "PRE_EXECUTION", source, source, fixture=True)[
            "decision"
        ]
        == "PASS"
    )
    # Provider mapping remains unresolved even when all symbolic fields exist.
    assert (
        da04.validate_payload(frame, destination, "PRE_EXECUTION", source, source)["decision"]
        == "REVIEW"
    )
    for field in source:
        missing = {f: v for f, v in source.items() if f != field}
        check = da04.validate_payload(
            frame, destination, "PRE_EXECUTION", missing, source, fixture=True
        )
        assert check["decision"] != "PASS"


@pytest.mark.parametrize("transform", ["MINIMIZE", "FORMAT_NORMALIZE", "OMIT", "UNDEFINED"])
def test_exact_contract_corruption_rejected(transform):
    matrix = copy.deepcopy(da04.read_json(ROOT / da04.MATRIX))
    amount = next(r for r in matrix["requirements"] if r["required_fields"] == ["amount"])
    amount["transform"] = [transform]
    amount["outbound_transform_by_destination"]["BLOCKCHAIN_EXECUTION_SYSTEM"] = transform
    assert da04.contract_violations(matrix, da04.read_json(ROOT / da04.PIPELINE))


def test_duplicate_or_incomplete_lineage_fails_closed():
    matrix = da04.read_json(ROOT / da04.MATRIX)
    reg = pd.read_csv(ROOT / da04.REQUIREMENTS, dtype=str, keep_default_na=False)
    mapping = pd.read_csv(ROOT / da04.MAPPING, dtype=str, keep_default_na=False)
    with pytest.raises(ValueError, match="Duplicate"):
        da04.normalize(matrix, pd.concat([reg, reg.iloc[[0]]]), mapping)
    with pytest.raises(ValueError, match="Unmatched"):
        da04.normalize(matrix, reg.iloc[1:], mapping)


def test_docs_links_and_no_personal_paths():
    docs = ROOT / da04.DA / "docs/handoff/DA_04_outbound_destination.md"
    for link in re.findall(r"\]\(([^)]+)\)", docs.read_text(encoding="utf-8")):
        if not link.startswith(("https://", "#")):
            assert (docs.parent / link.split("#")[0]).exists()
    nb = da04.read_json(ROOT / da04.NOTEBOOK)
    sources = "\n".join("".join(c["source"]) for c in nb["cells"])
    assert not re.search(r"[A-Z]:[\\/]Users[\\/]", sources)
