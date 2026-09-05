from types import SimpleNamespace
from pathlib import Path

import pytest

from rigorpath_web_test.pytest_plugin import pytest_collection_modifyitems
from rigorpath_web_test.config import WebTestConfig
from rigorpath_web_test.pytest_plugin import web_context


class FakeItem:
    nodeid = "tests/test_checkout.py::test_pay"
    fixturenames = ["web_page", "web_observer"]

    def __init__(self, marker):
        self.marker = marker

    def get_closest_marker(self, name):
        assert name == "rigor_source"
        return self.marker


def test_collection_rejects_missing_web_traceability():
    with pytest.raises(pytest.UsageError, match="missing @pytest.mark.rigor_source"):
        pytest_collection_modifyitems([FakeItem(None)])


def test_collection_accepts_complete_web_traceability():
    marker = SimpleNamespace(
        args=(),
        kwargs={
            "automation_id": "AUTO-001",
            "test_points": ["TP-001"],
            "test_cases": ["TC-001"],
        },
    )
    pytest_collection_modifyitems([FakeItem(marker)])


def test_web_context_uses_managed_factory_and_storage_state(tmp_path: Path):
    calls = []
    context = SimpleNamespace(close=lambda: calls.append("closed"))

    def new_context(**kwargs):
        calls.append(kwargs)
        return context

    config = WebTestConfig("https://example.test/", tmp_path, 1000)
    fixture = web_context.__wrapped__(config, {"cookies": []}, new_context)
    assert next(fixture) is context
    with pytest.raises(StopIteration):
        next(fixture)
    assert calls == [
        {"base_url": "https://example.test/", "storage_state": {"cookies": []}},
        "closed",
    ]
