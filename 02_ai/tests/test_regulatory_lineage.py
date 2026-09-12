import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_regulatory_lineage import validate  # noqa: E402


def test_regulatory_baseline_and_lineage_are_consistent() -> None:
    validate()
