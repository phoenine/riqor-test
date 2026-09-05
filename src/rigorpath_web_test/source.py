from __future__ import annotations

import re
from typing import Any, Mapping


REFERENCE_PATTERNS = {
    "requirements": re.compile(r"^REQ-\d+$"),
    "business_rules": re.compile(r"^BR-\d+$"),
    "questions": re.compile(r"^Q-\d+$"),
    "risks": re.compile(r"^RISK-\d+$"),
    "test_points": re.compile(r"^TP-\d+$"),
    "test_cases": re.compile(r"^TC-\d+$"),
    "data_rows": re.compile(r"^DATA-\d+$"),
}
AUTO_ID_PATTERN = re.compile(r"^AUTO-\d+$")


def validate_source_metadata(
    metadata: Mapping[str, Any], where: str = "web testcase"
) -> list[str]:
    errors: list[str] = []
    allowed = {"automation_id", *REFERENCE_PATTERNS}
    for key in sorted(set(metadata) - allowed):
        errors.append(f"{where}: unknown rigor_source field {key!r}")

    automation_id = metadata.get("automation_id")
    if not isinstance(automation_id, str) or not AUTO_ID_PATTERN.fullmatch(
        automation_id
    ):
        errors.append(f"{where}.automation_id: must match AUTO-###")

    for field, pattern in REFERENCE_PATTERNS.items():
        values = metadata.get(field, [])
        if not isinstance(values, (list, tuple)) or any(
            not isinstance(value, str) or not pattern.fullmatch(value)
            for value in values
        ):
            errors.append(f"{where}.{field}: invalid reference list")
    for required in ("test_points", "test_cases"):
        if not metadata.get(required):
            errors.append(f"{where}.{required}: at least one reference is required")
    return errors
