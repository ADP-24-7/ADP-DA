from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "regulatory_baseline"
SNAPSHOT = BASELINE / "OFFICIAL_REGULATORY_SNAPSHOT_2026-09-12.json"
REGISTRIES = (
    BASELINE / "AI_REGULATORY_REGISTRY.json",
    BASELINE / "DIGITAL_ASSET_REGULATORY_REGISTRY.json",
)


class Fetcher(Protocol):
    def __call__(self, source: Mapping[str, Any]) -> bytes: ...


class Parser(Protocol):
    def __call__(self, source: Mapping[str, Any], content: bytes) -> list[str]: ...


@dataclass(frozen=True)
class RefreshCandidate:
    candidate_type: str
    candidate_id: str
    status: str = "PENDING_REVIEW"


@dataclass(frozen=True)
class RefreshResult:
    source_id: str
    regulatory_evidence_id: str
    status: str
    previous_digest: str
    current_digest: str | None
    changed_scope: tuple[str, ...]
    impact_domains: tuple[str, ...]
    candidates: tuple[RefreshCandidate, ...]
    parser_runs: int
    automatic_activation: bool = False
    error: str | None = None


def normalize_content(content: bytes) -> bytes:
    """Create a stable digest input without changing the official source payload."""
    text = content.decode("utf-8", errors="replace").replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text.encode("utf-8")


def content_digest(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(normalize_content(content)).hexdigest()


class OfficialSourceAdapter:
    """Canonical HTTP adapter; authority-specific subclasses isolate source quirks."""

    hosts: tuple[str, ...] = ()

    def supports(self, source: Mapping[str, Any]) -> bool:
        url = str(source["official_url"])
        return any(host in url for host in self.hosts)

    def fetch(self, source: Mapping[str, Any]) -> bytes:
        request = urllib.request.Request(
            str(source["official_url"]),
            headers={"User-Agent": "ADP-Regulatory-Refresh/1.0"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return cast(bytes, response.read())


class LawGoKrAdapter(OfficialSourceAdapter):
    hosts = ("law.go.kr",)


class FinancialServicesCommissionAdapter(OfficialSourceAdapter):
    hosts = ("fsc.go.kr",)


class KoreaFinancialIntelligenceUnitAdapter(OfficialSourceAdapter):
    hosts = ("kofiu.go.kr",)


class PersonalInformationProtectionCommissionAdapter(OfficialSourceAdapter):
    hosts = ("pipc.go.kr",)


class FinancialSecurityInstituteAdapter(OfficialSourceAdapter):
    hosts = ("fsec.or.kr",)


class FatfAdapter(OfficialSourceAdapter):
    hosts = ("fatf-gafi.org",)


class GenericOfficialAdapter(OfficialSourceAdapter):
    def supports(self, source: Mapping[str, Any]) -> bool:
        return str(source["official_url"]).startswith("https://")


DEFAULT_ADAPTERS = (
    LawGoKrAdapter(),
    FinancialServicesCommissionAdapter(),
    KoreaFinancialIntelligenceUnitAdapter(),
    PersonalInformationProtectionCommissionAdapter(),
    FinancialSecurityInstituteAdapter(),
    FatfAdapter(),
    GenericOfficialAdapter(),
)


def fetch_official_source(source: Mapping[str, Any]) -> bytes:
    adapter = next(adapter for adapter in DEFAULT_ADAPTERS if adapter.supports(source))
    return adapter.fetch(source)


def default_parser(source: Mapping[str, Any], content: bytes) -> list[str]:
    del content
    return [str(article) for article in source.get("applicable_articles", [])]


def _domains(domain: str) -> tuple[str, ...]:
    if domain == "BOTH":
        return ("AI", "DIGITAL_ASSET")
    return (domain,)


def _candidate_id(source: Mapping[str, Any], candidate_type: str, digest: str) -> str:
    return f"{source['source_id']}:{candidate_type}:{digest.removeprefix('sha256:')[:12]}"


class RegulatoryRefreshService:
    def __init__(self, snapshot: Mapping[str, Any], registries: Iterable[Mapping[str, Any]]):
        self.sources = {str(item["source_id"]): item for item in snapshot["sources"]}
        self.mappings: dict[str, list[Mapping[str, Any]]] = {}
        for registry in registries:
            for entry in registry["entries"]:
                self.mappings.setdefault(str(entry["source_id"]), []).append(entry)

    def refresh(
        self,
        source_ids: Iterable[str] | None = None,
        *,
        fetcher: Fetcher = fetch_official_source,
        parser: Parser = default_parser,
    ) -> list[RefreshResult]:
        selected = list(source_ids) if source_ids is not None else list(self.sources)
        return [
            self._refresh_one(self.sources[source_id], fetcher, parser)
            for source_id in selected
        ]

    def _refresh_one(
        self, source: Mapping[str, Any], fetcher: Fetcher, parser: Parser
    ) -> RefreshResult:
        source_id = str(source["source_id"])
        evidence_id = str(source["regulatory_evidence_id"])
        previous = str(source["content_digest"])
        try:
            content = fetcher(source)
        except Exception as exc:  # source adapters intentionally fail closed
            return RefreshResult(
                source_id, evidence_id, "FETCH_FAILED", previous, None, (), (), (), 0,
                error=f"{type(exc).__name__}: {exc}",
            )
        current = content_digest(content)
        if current == previous:
            return RefreshResult(
                source_id, evidence_id, "UNCHANGED", previous, current, (), (), (), 0
            )
        try:
            changed_scope = tuple(parser(source, content))
        except Exception as exc:
            return RefreshResult(
                source_id, evidence_id, "PARSE_FAILED", previous, current, (), (), (), 1,
                error=f"{type(exc).__name__}: {exc}",
            )

        mappings = self.mappings.get(source_id, [])
        has_policy_impact = any(
            entry.get("linked_requirements") and entry.get("linked_controls") for entry in mappings
        )
        domains = _domains(str(source["domain"])) if has_policy_impact else ()
        if not has_policy_impact:
            return RefreshResult(
                source_id, evidence_id, "NO_POLICY_IMPACT", previous, current,
                changed_scope, (), (), 1,
            )

        candidate_types = (
            "REGULATORY_EVIDENCE_VERSION",
            "REQUIREMENT_CONTROL",
            "POLICY",
        )
        candidates = tuple(
            RefreshCandidate(kind, _candidate_id(source, kind, current))
            for kind in candidate_types
        )
        return RefreshResult(
            source_id, evidence_id, "CHANGED", previous, current,
            changed_scope, domains, candidates, 1,
        )


def load_service() -> RegulatoryRefreshService:
    snapshot = cast(dict[str, Any], json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    registries = [
        cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        for path in REGISTRIES
    ]
    return RegulatoryRefreshService(snapshot, registries)


def scheduled_refresh_enabled() -> bool:
    return os.getenv("REGULATORY_REFRESH_ENABLED", "false").lower() == "true"


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh canonical official regulatory sources")
    parser.add_argument("--source-id", action="append", dest="source_ids")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    results = load_service().refresh(args.source_ids)
    report = {
        "refreshed_at": datetime.now(UTC).isoformat(),
        "automatic_activation": False,
        "results": [asdict(result) for result in results],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
