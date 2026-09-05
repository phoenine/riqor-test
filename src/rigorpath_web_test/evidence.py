from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _safe_name(value: str, max_length: int = 120) -> str:
    normalized = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("_")
    return normalized[:max_length] or "test"


def _redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        netloc = f"{hostname}{port}"
        query = urlencode(
            [(key, "REDACTED") for key, _ in parse_qsl(parsed.query)]
        )
        return urlunsplit((parsed.scheme, netloc, parsed.path, query, parsed.fragment))
    except (TypeError, ValueError):
        return "<unavailable>"


def _event_value(event: Any, name: str) -> str:
    value = getattr(event, name, "")
    return str(value() if callable(value) else value)


@dataclass
class _ObservedPage:
    page: Any
    console: list[str] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    console_handler: Any = None
    error_handler: Any = None


class WebEvidenceCollector:
    """Observe one or more Playwright pages and persist evidence on failure."""

    def __init__(self, artifacts_dir: Path, timeout_ms: int = 10_000) -> None:
        self.artifacts_dir = artifacts_dir
        self.timeout_ms = timeout_ms
        self._pages: dict[int, _ObservedPage] = {}
        self._captured_phases: set[str] = set()

    def observe(self, page: Any) -> Any:
        key = id(page)
        if key in self._pages:
            return page

        observed = _ObservedPage(page=page)

        def on_console(message: Any) -> None:
            observed.console.append(
                f"[{_event_value(message, 'type')}] {_event_value(message, 'text')}"
            )

        def on_page_error(error: Any) -> None:
            observed.page_errors.append(str(error))

        observed.console_handler = on_console
        observed.error_handler = on_page_error
        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.set_default_timeout(self.timeout_ms)
        page.set_default_navigation_timeout(self.timeout_ms)
        self._pages[key] = observed
        return page

    def capture_failure(self, nodeid: str, phase: str) -> Path | None:
        if not self._pages or phase in self._captured_phases:
            return None
        self._captured_phases.add(phase)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        output_dir = self.artifacts_dir / f"{timestamp}_{_safe_name(nodeid)}_{phase}"
        output_dir.mkdir(parents=True, exist_ok=False)

        pages_meta: list[dict[str, Any]] = []
        capture_errors: list[str] = []
        for index, observed in enumerate(self._pages.values(), 1):
            page = observed.page
            try:
                url = _redact_url(str(page.url))
            except Exception:
                url = "<unavailable>"
            try:
                title = page.title()
            except Exception:
                title = "<unavailable>"

            pages_meta.append({"index": index, "url": url, "title": title})
            try:
                page.screenshot(path=str(output_dir / f"page-{index}.png"), full_page=True)
            except Exception as exc:
                capture_errors.append(f"page-{index} screenshot: {exc}")
            (output_dir / f"page-{index}-console.log").write_text(
                "\n".join(observed.console), encoding="utf-8"
            )
            (output_dir / f"page-{index}-pageerror.log").write_text(
                "\n".join(observed.page_errors), encoding="utf-8"
            )

        metadata = {
            "nodeid": nodeid,
            "phase": phase,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "pages": pages_meta,
            "capture_errors": capture_errors,
        }
        (output_dir / "meta.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return output_dir

    def close(self) -> None:
        for observed in self._pages.values():
            try:
                observed.page.off("console", observed.console_handler)
                observed.page.off("pageerror", observed.error_handler)
            except Exception:
                pass
