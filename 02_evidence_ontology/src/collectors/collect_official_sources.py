from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = ROOT / "config" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"


def read_sources(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    items: list[dict] = []
    current: dict[str, str] | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("  - "):
            if current:
                items.append(current)
            current = {}
            key, value = line[4:].split(":", 1)
            current[key.strip()] = value.strip().strip('"')
        elif current is not None and line.startswith("    ") and ":" in line:
            key, value = line.strip().split(":", 1)
            current[key.strip()] = value.strip().strip('"')
    if current:
        items.append(current)
    return items


def safe_name(source_id: str, suffix: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", source_id) + suffix


def collect_webpage(source: dict) -> dict:
    url = source["official_url"]
    request = Request(url, headers={"User-Agent": "FinancialPrivacyGatewayEvidenceCollector/0.1"})
    with urlopen(request, timeout=20) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")
    suffix = ".pdf" if "pdf" in content_type.lower() or url.lower().endswith(".pdf") else ".html"
    raw_path = RAW_DIR / safe_name(source["source_id"], suffix)
    raw_path.write_bytes(body)
    return {
        "source_id": source["source_id"],
        "status": "COLLECTED",
        "raw_path": str(raw_path.relative_to(ROOT)),
        "source_url": url,
        "document_name": source["document_name"],
        "effective_date": source.get("effective_date", ""),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources = read_sources(SOURCES_PATH)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": [],
    }
    for source in sources:
        if source.get("collection_method") not in {"official_webpage"}:
            manifest["sources"].append({
                "source_id": source["source_id"],
                "status": "MANUAL_REQUIRED",
                "reason": "Configured as attachment/manual collection; do not infer or bypass download URLs.",
            })
            continue
        try:
            manifest["sources"].append(collect_webpage(source))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            manifest["sources"].append({
                "source_id": source["source_id"],
                "status": "MANUAL_REQUIRED",
                "reason": f"Automated official webpage collection failed: {exc}",
            })
    (RAW_DIR / "collection_manifest.generated.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
