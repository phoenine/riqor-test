import pytest

from rigorpath_web_test.source import validate_source_metadata


def valid_source():
    return {
        "automation_id": "AUTO-001",
        "requirements": ["REQ-001"],
        "business_rules": [],
        "questions": [],
        "risks": ["RISK-001"],
        "test_points": ["TP-001"],
        "test_cases": ["TC-001"],
        "data_rows": [],
    }


def test_valid_source_metadata_passes():
    assert validate_source_metadata(valid_source()) == []


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"automation_id": "TC-001"}, "automation_id"),
        ({"test_points": []}, "at least one"),
        ({"test_cases": ["AUTO-001"]}, "invalid reference list"),
        ({"extra": ["REQ-001"]}, "unknown rigor_source field"),
    ],
)
def test_invalid_source_metadata_fails_closed(change, message):
    source = valid_source()
    source.update(change)
    assert any(message in error for error in validate_source_metadata(source))
