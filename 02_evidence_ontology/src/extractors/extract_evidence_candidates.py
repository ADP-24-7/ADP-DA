from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARSED_PATH = ROOT / "data" / "parsed" / "parsed_segments.json"
REVIEWED_PATH = ROOT / "data" / "reviewed" / "evidence_candidates.json"


def first_present(text: str, candidates: list[str]) -> str | None:
    return next((candidate for candidate in candidates if candidate in text), None)


def extract_candidate(segment: dict, index: int) -> dict:
    text = segment["original_text"]
    required_action = first_present(
        text,
        [
            "동의를 받아야 한다",
            "확인하여야 한다",
            "수행한다",
            "승인을 받아야 한다",
            "조치를 하여야 한다",
            "기록을 작성하여 보관하여야 하며",
            "처리를 중지하고, 지체 없이 회수ㆍ파기하여야 한다",
            "조치를 완료하여야 한다",
        ],
    )
    prohibition = first_present(
        text,
        [
            "포함해서는 아니 된다",
            "처리해서는 아니 된다",
        ],
    )
    exception = first_present(
        text,
        [
            "동의 없이",
            "다만",
            "제28조의2에도 불구하고",
        ],
    )
    data_type = first_present(
        text,
        [
            "가명정보",
            "개인신용정보",
            "특정 개인을 알아볼 수 있는 정보",
        ],
    )
    applies_to = first_present(
        text,
        [
            "개인정보처리자",
            "신용정보제공ㆍ이용자",
            "신용조회회사",
            "신용정보집중기관",
            "개인인 신용정보주체",
        ],
    )
    condition = first_present(
        text,
        [
            "통계작성, 과학적 연구, 공익적 기록보존",
            "제3자에게 제공하는 경우",
            "기관 외부로 결합된 정보를 반출하려는",
            "가명정보를 처리하는 경우",
            "가명정보를 처리하고자 하는 경우",
            "특정 개인을 알아볼 수 있는 정보가 생성된 경우",
            "청구를 받은 날부터 1개월 이내",
        ],
    )
    review_status = (
        "PENDING" if any([required_action, prohibition, exception]) else "REVIEW_REQUIRED"
    )
    return {
        "evidence_id": f"EV-{index:05d}",
        **segment,
        "applies_to": applies_to,
        "data_type": data_type,
        "condition": condition,
        "required_action": required_action,
        "prohibition": prohibition,
        "exception": exception,
        "review_status": review_status,
    }


def main() -> None:
    parsed = json.loads(PARSED_PATH.read_text(encoding="utf-8"))
    candidates = [
        extract_candidate(segment, index) for index, segment in enumerate(parsed, start=1)
    ]
    REVIEWED_PATH.parent.mkdir(parents=True, exist_ok=True)
    REVIEWED_PATH.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
