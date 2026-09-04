from pathlib import Path

import pytest

from rigorpath_api_test.validation import CaseContractError, load_suites, validate_suite


def valid_suite():
    return {
        "schema_version": 1,
        "suite": "accounts",
        "required_env": ["ACCOUNT_ID"],
        "cases": [
            {
                "id": "AUTO-001",
                "title": "Existing account is returned",
                "source": {
                    "requirements": ["REQ-001"],
                    "business_rules": [],
                    "questions": [],
                    "risks": ["RISK-001"],
                    "test_points": ["TP-001"],
                    "test_cases": ["TC-001"],
                    "data_rows": ["DATA-001"],
                },
                "side_effect": "none",
                "request": {"method": "GET", "path": "/accounts/${ACCOUNT_ID}"},
                "assertions": [
                    {
                        "type": "requirement",
                        "source": "REQ-001",
                        "target": "status",
                        "matcher": "eq",
                        "expected": 200,
                    }
                ],
            }
        ],
    }


def test_valid_suite_passes():
    assert validate_suite(valid_suite()) == []


def test_missing_env_declaration_and_tautology_fail():
    suite = valid_suite()
    suite["required_env"] = []
    suite["cases"][0]["assertions"][0].update(
        {"target": "text", "matcher": "contains", "expected": ""}
    )
    errors = validate_suite(suite)
    assert any("not listed in required_env" in error for error in errors)
    assert any("tautological" in error for error in errors)


def test_invalid_yaml_is_not_silently_skipped(tmp_path: Path):
    path = tmp_path / "broken.yaml"
    path.write_text("cases: [", encoding="utf-8")
    with pytest.raises(CaseContractError, match="broken.yaml"):
        load_suites([path])


def test_duplicate_auto_ids_across_files_fail(tmp_path: Path):
    import yaml

    for name in ("one.yaml", "two.yaml"):
        (tmp_path / name).write_text(
            yaml.safe_dump(valid_suite(), allow_unicode=True), encoding="utf-8"
        )
    with pytest.raises(CaseContractError, match="duplicate AUTO-001"):
        load_suites([tmp_path])
