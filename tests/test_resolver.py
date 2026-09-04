import pytest

from rigorpath_api_test.resolver import resolve


def test_resolves_environment_and_capture_without_losing_types():
    value = {"id": "${ACCOUNT_ID}", "created": "${cache.created_id}"}
    assert resolve(value, {"ACCOUNT_ID": "42"}, {"created_id": 7}) == {
        "id": "42",
        "created": 7,
    }


def test_missing_values_fail_closed():
    with pytest.raises(KeyError, match="missing required environment"):
        resolve("${TOKEN}", {}, {})
