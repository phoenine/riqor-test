from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit


class WebTestConfigError(ValueError):
    """Raised when the generic web runtime configuration is invalid."""


@dataclass(frozen=True)
class WebTestConfig:
    base_url: str
    artifacts_dir: Path
    timeout_ms: int

    @classmethod
    def load(
        cls,
        *,
        base_url: str | None = None,
        artifacts_dir: str | Path | None = None,
        timeout_ms: int | str | None = None,
        rootpath: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> "WebTestConfig":
        values = os.environ if env is None else env
        resolved_base_url = (base_url or values.get("WEBTEST_BASE_URL", "")).strip()
        parsed = urlsplit(resolved_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise WebTestConfigError(
                "WEBTEST_BASE_URL or --web-base-url must be an absolute HTTP(S) URL"
            )

        raw_artifacts = artifacts_dir or values.get("WEBTEST_ARTIFACTS_DIR", "artifacts")
        resolved_artifacts = Path(raw_artifacts)
        if not resolved_artifacts.is_absolute():
            resolved_artifacts = (rootpath or Path.cwd()) / resolved_artifacts

        raw_timeout = (
            timeout_ms
            if timeout_ms is not None
            else values.get("WEBTEST_TIMEOUT_MS", "10000")
        )
        try:
            resolved_timeout = int(raw_timeout)
        except (TypeError, ValueError) as exc:
            raise WebTestConfigError("WEBTEST_TIMEOUT_MS must be an integer") from exc
        if resolved_timeout <= 0:
            raise WebTestConfigError("WEBTEST_TIMEOUT_MS must be greater than zero")

        return cls(
            base_url=resolved_base_url.rstrip("/") + "/",
            artifacts_dir=resolved_artifacts.resolve(),
            timeout_ms=resolved_timeout,
        )
