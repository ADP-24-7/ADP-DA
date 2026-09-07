"""DA-05 executable contract reference; not a BE adapter or an approval issuer."""

from __future__ import annotations

import re
from datetime import UTC, datetime


class MatchContractError(ValueError):
    """Malformed/unbound inputs fail closed before rule comparison."""


def atomic(value: object) -> int:
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    raise MatchContractError("EXACT_AMOUNT_REQUIRED")


def instant(value: object) -> datetime:
    try:
        if not isinstance(value, str):
            raise TypeError
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(UTC)
    except (TypeError, ValueError) as exc:
        raise MatchContractError("TIMEZONE_AWARE_TIMESTAMP_REQUIRED") from exc


def address(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise MatchContractError("ETHEREUM_ADDRESS_REQUIRED")
    return value.lower()


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MatchContractError("REQUIRED_INPUT_MISSING")
    return value


def evaluate(
    approval: dict,
    request: dict,
    binding: dict,
    *,
    evaluated_at: str,
    contract_version: str,
    evidence_reference: str,
) -> dict:
    """Explicit trusted binding; invalid input returns no PASS (raises contract error).

    request_type is structural context, not EIP transaction_type. Upstream must
    establish creation context; missing an ordinary destination alone cannot bypass a rule.
    """
    try:
        aid, rid = text(approval["approval_id"]), text(request["request_id"])
        if binding != {"approval_id": aid, "request_id": rid}:
            raise MatchContractError("APPROVAL_REQUEST_BINDING_FAILED")
        if "contract_address" in request:
            raise MatchContractError("POST_EXECUTION_FIELD_FORBIDDEN")
        structure = request["request_type"]
        if structure not in {"ADDRESS_TRANSACTION", "CONTRACT_CREATION"}:
            raise MatchContractError("STRUCTURE_UNRESOLVED")
        # EIP type is trace context only, never a policy allow/block lookup.
        if type(request["transaction_type"]) is not int or request["transaction_type"] < 0:
            raise MatchContractError("INVALID_TRANSACTION_TYPE_CONTEXT")
        start, end = instant(approval["valid_from"]), instant(approval["valid_until"])
        when = instant(request["requested_at"])
        if start > end:
            raise MatchContractError("INVALID_APPROVAL_PERIOD")
        results = {
            "asset_match": text(request["requested_asset"]) == text(approval["approved_asset"]),
            "amount_match": atomic(request["requested_amount"])
            <= atomic(approval["approved_max_amount"]),
            "period_match": start <= when <= end,
        }
        applicable = structure == "ADDRESS_TRANSACTION"
        if applicable:
            destination = address(request["requested_destination"]) == address(
                approval["approved_destination"]
            )
        else:
            if request.get("requested_destination") not in (None, ""):
                raise MatchContractError("CREATION_DESTINATION_SUBSTITUTION_FORBIDDEN")
            if approval.get("approved_destination") not in (None, ""):
                raise MatchContractError("CREATION_APPROVAL_DESTINATION_CONFLICT")
            destination = None
        results["destination_match"] = destination
        violations = [name for name, matched in results.items() if matched is False]
        instant(evaluated_at)
        return {
            "approval_id": aid,
            "request_id": rid,
            "source_phase": "PRE_EXECUTION",
            "request_type": structure,
            "transaction_type": request["transaction_type"],
            "rule_applicability": {
                "asset": "APPLICABLE",
                "amount": "APPLICABLE",
                "destination": "APPLICABLE" if applicable else "NOT_APPLICABLE",
                "period": "APPLICABLE",
            },
            "destination_applicability": "APPLICABLE" if applicable else "NOT_APPLICABLE",
            **results,
            "violation_reasons": violations,
            "violation_count": len(violations),
            "approval_match": not violations,
            "decision": "BLOCK" if violations else "PASS",
            "evaluated_at": evaluated_at,
            "contract_version": text(contract_version),
            "validation_evidence_reference": text(evidence_reference),
        }
    except KeyError as exc:
        raise MatchContractError("REQUIRED_INPUT_MISSING") from exc
