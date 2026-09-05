import json
from pathlib import Path

from rigorpath_web_test import WebEvidenceCollector


class FakeConsoleMessage:
    type = "warning"
    text = "slow response"


class FakePage:
    url = "https://user:secret@example.test/path?token=secret&view=full"

    def __init__(self):
        self.handlers = {}
        self.timeouts = []

    def on(self, event, handler):
        self.handlers[event] = handler

    def off(self, event, handler):
        assert self.handlers[event] is handler
        del self.handlers[event]

    def set_default_timeout(self, timeout):
        self.timeouts.append(("action", timeout))

    def set_default_navigation_timeout(self, timeout):
        self.timeouts.append(("navigation", timeout))

    def title(self):
        return "Example"

    def screenshot(self, *, path, full_page):
        assert full_page is True
        Path(path).write_bytes(b"png")


def test_failure_evidence_is_written_and_url_secrets_are_redacted(tmp_path: Path):
    page = FakePage()
    collector = WebEvidenceCollector(tmp_path, timeout_ms=3210)
    assert collector.observe(page) is page
    assert collector.observe(page) is page
    page.handlers["console"](FakeConsoleMessage())
    page.handlers["pageerror"](RuntimeError("boom"))

    output = collector.capture_failure("cases/test_checkout.py::test_pay", "call")

    assert output is not None
    assert (output / "page-1.png").read_bytes() == b"png"
    assert (output / "page-1-console.log").read_text() == "[warning] slow response"
    assert (output / "page-1-pageerror.log").read_text() == "boom"
    metadata = json.loads((output / "meta.json").read_text())
    assert metadata["phase"] == "call"
    assert metadata["pages"][0]["url"] == (
        "https://example.test/path?token=REDACTED&view=REDACTED"
    )
    assert page.timeouts == [("action", 3210), ("navigation", 3210)]
    assert collector.capture_failure("same", "call") is None

    collector.close()
    assert page.handlers == {}
