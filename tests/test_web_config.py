from pathlib import Path

import pytest

from rigorpath_web_test import WebTestConfig, WebTestConfigError


def test_loads_generic_web_config_with_cli_precedence(tmp_path: Path):
    config = WebTestConfig.load(
        base_url="https://cli.example.test/app",
        artifacts_dir="evidence",
        timeout_ms=2500,
        rootpath=tmp_path,
        env={"WEBTEST_BASE_URL": "https://env.example.test"},
    )
    assert config.base_url == "https://cli.example.test/app/"
    assert config.artifacts_dir == (tmp_path / "evidence").resolve()
    assert config.timeout_ms == 2500


@pytest.mark.parametrize(
    ("configured_url", "timeout_ms", "message"),
    [
        ("", 1000, "absolute HTTP"),
        ("example.test", 1000, "absolute HTTP"),
        ("https://example.test", 0, "greater than zero"),
        ("https://example.test", "soon", "must be an integer"),
    ],
)
def test_invalid_web_config_fails_closed(configured_url, timeout_ms, message):
    with pytest.raises(WebTestConfigError, match=message):
        WebTestConfig.load(base_url=configured_url, timeout_ms=timeout_ms, env={})
