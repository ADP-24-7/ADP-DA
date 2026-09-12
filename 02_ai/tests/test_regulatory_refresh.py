from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from scripts.regulatory_refresh import RegulatoryRefreshService, content_digest


def source(source_id: str, domain: str, content: bytes = b"old") -> dict[str, Any]:
    return {
        "source_id": source_id,
        "regulatory_evidence_id": f"REF-{source_id}",
        "domain": domain,
        "official_url": f"https://official.example/{source_id}",
        "content_digest": content_digest(content),
        "applicable_articles": ["section-1"],
    }


def registry_entry(source_id: str, *, impacted: bool = True) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "linked_requirements": ["REQ-1"] if impacted else [],
        "linked_controls": ["CTRL-1"] if impacted else [],
    }


def service(*sources: Mapping[str, Any], impacted: bool = True) -> RegulatoryRefreshService:
    entries = [registry_entry(str(item["source_id"]), impacted=impacted) for item in sources]
    return RegulatoryRefreshService({"sources": list(sources)}, [{"entries": entries}])


def test_unchanged_skips_parser_and_candidates() -> None:
    item = source("AI-1", "AI")
    parser_runs = 0

    def parser(_source: Mapping[str, Any], _content: bytes) -> list[str]:
        nonlocal parser_runs
        parser_runs += 1
        return ["section-1"]

    result = service(item).refresh(fetcher=lambda _: b"old", parser=parser)[0]

    assert result.status == "UNCHANGED"
    assert result.parser_runs == parser_runs == 0
    assert result.candidates == ()


@pytest.mark.parametrize(
    ("domain", "expected"),
    [("AI", ("AI",)), ("DIGITAL_ASSET", ("DIGITAL_ASSET",)),
     ("BOTH", ("AI", "DIGITAL_ASSET"))],
)
def test_changed_source_is_split_by_registry_domain(
    domain: str, expected: tuple[str, ...]
) -> None:
    result = service(source("SOURCE-1", domain)).refresh(fetcher=lambda _: b"changed")[0]

    assert result.status == "CHANGED"
    assert result.impact_domains == expected
    assert {candidate.candidate_type for candidate in result.candidates} == {
        "REGULATORY_EVIDENCE_VERSION", "REQUIREMENT_CONTROL", "POLICY"
    }
    assert all(candidate.status == "PENDING_REVIEW" for candidate in result.candidates)
    assert result.automatic_activation is False


def test_fetch_failure_preserves_active_state_and_creates_nothing() -> None:
    def fail(_source: Mapping[str, Any]) -> bytes:
        raise OSError("official source unavailable")

    result = service(source("AI-1", "AI")).refresh(fetcher=fail)[0]

    assert result.status == "FETCH_FAILED"
    assert result.current_digest is None
    assert result.parser_runs == 0
    assert result.candidates == ()


def test_parse_failure_is_audited_without_candidates() -> None:
    def fail(_source: Mapping[str, Any], _content: bytes) -> list[str]:
        raise ValueError("unsupported source response")

    result = service(source("DA-1", "DIGITAL_ASSET")).refresh(
        fetcher=lambda _: b"changed", parser=fail
    )[0]

    assert result.status == "PARSE_FAILED"
    assert result.error == "ValueError: unsupported source response"
    assert result.candidates == ()


def test_changed_source_without_policy_impact_creates_no_candidates() -> None:
    item = source("AI-1", "AI")
    result = service(item, impacted=False).refresh(fetcher=lambda _: b"changed")[0]

    assert result.status == "NO_POLICY_IMPACT"
    assert result.candidates == ()
