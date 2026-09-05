from __future__ import annotations

import os
from pathlib import Path

import pytest

from .config import WebTestConfig, WebTestConfigError
from .evidence import WebEvidenceCollector
from .source import validate_source_metadata


WEB_FIXTURES = {"web_context", "web_page", "web_observer"}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("rigorpath-web-test")
    group.addoption("--web-base-url", help="Absolute URL of the web application under test")
    group.addoption(
        "--web-artifacts-dir",
        help="Failure artifact directory, relative to the pytest root by default",
    )
    group.addoption("--web-timeout-ms", type=int, help="Default Playwright timeout")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "rigor_source(automation_id, test_points, test_cases, ...): "
        "traceability metadata required by rigorpath Web testcases",
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    errors: list[str] = []
    for item in items:
        if not WEB_FIXTURES.intersection(item.fixturenames):
            continue
        marker = item.get_closest_marker("rigor_source")
        if marker is None:
            errors.append(f"{item.nodeid}: missing @pytest.mark.rigor_source")
            continue
        if marker.args:
            errors.append(f"{item.nodeid}: rigor_source accepts keyword arguments only")
            continue
        errors.extend(validate_source_metadata(marker.kwargs, item.nodeid))
    if errors:
        raise pytest.UsageError("invalid Web testcase traceability:\n- " + "\n- ".join(errors))


@pytest.fixture(scope="session")
def webtest_config(pytestconfig: pytest.Config) -> WebTestConfig:
    base_url = pytestconfig.getoption("--web-base-url")
    if not base_url and not os.environ.get("WEBTEST_BASE_URL"):
        pytest.skip("WEBTEST_BASE_URL or --web-base-url is required for Web execution")
    try:
        return WebTestConfig.load(
            base_url=base_url,
            artifacts_dir=pytestconfig.getoption("--web-artifacts-dir"),
            timeout_ms=pytestconfig.getoption("--web-timeout-ms"),
            rootpath=Path(pytestconfig.rootpath),
        )
    except WebTestConfigError as exc:
        raise pytest.UsageError(str(exc)) from exc


@pytest.fixture(scope="session")
def web_storage_state():
    """Override in a business repository to supply Playwright storage state."""
    return None


@pytest.fixture
def web_context(webtest_config: WebTestConfig, web_storage_state, new_context):
    context_args = {"base_url": webtest_config.base_url}
    if web_storage_state is not None:
        context_args["storage_state"] = web_storage_state
    context = new_context(**context_args)
    yield context
    context.close()


@pytest.fixture
def web_observer(request: pytest.FixtureRequest, webtest_config: WebTestConfig):
    collector = WebEvidenceCollector(
        webtest_config.artifacts_dir, timeout_ms=webtest_config.timeout_ms
    )
    setattr(request.node, "_rigorpath_web_observer", collector)
    yield collector
    collector.close()


@pytest.fixture
def web_page(web_observer: WebEvidenceCollector, web_context):
    """A pytest-playwright page with failure evidence enabled."""
    return web_observer.observe(web_context.new_page())


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if not report.failed:
        return
    collector = getattr(item, "_rigorpath_web_observer", None)
    if collector is not None:
        collector.capture_failure(item.nodeid, report.when)
