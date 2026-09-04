from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urljoin

import httpx

from .assertions import check, jsonpath_get
from .resolver import resolve


@dataclass(frozen=True)
class ExecutionResult:
    case_id: str
    status_code: int
    duration_ms: float
    response: Any


class ApiSession:
    def __init__(
        self,
        base_url: str,
        *,
        env: Mapping[str, str] | None = None,
        verify: bool = True,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/") + "/"
        self.env = dict(os.environ if env is None else env)
        self.cache: dict[str, Any] = {}
        self.client = httpx.Client(verify=verify, timeout=timeout, transport=transport)

    def close(self) -> None:
        self.client.close()

    def execute(self, case: dict[str, Any]) -> ExecutionResult:
        primary_error: BaseException | None = None
        try:
            result = self._request(case["id"], case["request"])
            self._assert(result, case["assertions"])
            self._capture(result.response, case.get("capture", []))
            return result
        except BaseException as exc:
            primary_error = exc
            raise
        finally:
            if case.get("cleanup"):
                try:
                    cleanup = self._request(f"{case['id']}:cleanup", case["cleanup"])
                    if cleanup.status_code >= 400:
                        raise AssertionError(f"cleanup returned HTTP {cleanup.status_code}")
                except BaseException as cleanup_error:
                    if primary_error is not None:
                        primary_error.add_note(f"cleanup failed: {cleanup_error}")
                    else:
                        raise

    def _request(self, case_id: str, request: dict[str, Any]) -> ExecutionResult:
        resolved = resolve(request, self.env, self.cache)
        kwargs: dict[str, Any] = {
            "headers": resolved.get("headers"),
            "params": resolved.get("query"),
            "json": resolved.get("json"),
        }
        if "timeout_seconds" in resolved:
            kwargs["timeout"] = resolved["timeout_seconds"]
        started = time.perf_counter()
        response = self.client.request(
            resolved["method"],
            urljoin(self.base_url, resolved["path"].lstrip("/")),
            **kwargs,
        )
        duration_ms = (time.perf_counter() - started) * 1000
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        return ExecutionResult(
            case_id=case_id,
            status_code=response.status_code,
            duration_ms=duration_ms,
            response=body,
        )

    def _assert(self, result: ExecutionResult, assertions: list[dict[str, Any]]) -> None:
        for assertion in assertions:
            target = assertion["target"]
            actual = {
                "status": result.status_code,
                "duration_ms": result.duration_ms,
                "text": result.response,
            }.get(target)
            if target == "jsonpath":
                actual = jsonpath_get(result.response, assertion["path"])
            check(actual, assertion["matcher"], assertion["expected"])

    def _capture(self, body: Any, captures: list[dict[str, str]]) -> None:
        for capture in captures:
            self.cache[capture["name"]] = jsonpath_get(body, capture["path"])

    def __enter__(self) -> "ApiSession":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
