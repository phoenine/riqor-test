from __future__ import annotations

from typing import Any


def jsonpath_get(data: Any, path: str) -> Any:
    if path == "$":
        return data
    if not path.startswith("$."):
        raise AssertionError(f"unsupported JSONPath: {path}")
    current = data
    for part in path[2:].split("."):
        if "[" in part and part.endswith("]"):
            name, raw_index = part[:-1].split("[", 1)
            if name:
                current = current[name]
            current = current[int(raw_index)]
        else:
            current = current[part]
    return current


def check(actual: Any, matcher: str, expected: Any) -> None:
    operations = {
        "eq": lambda: actual == expected,
        "ne": lambda: actual != expected,
        "lt": lambda: actual < expected,
        "lte": lambda: actual <= expected,
        "gt": lambda: actual > expected,
        "gte": lambda: actual >= expected,
        "contains": lambda: expected in actual,
        "len_eq": lambda: len(actual) == expected,
        "len_gt": lambda: len(actual) > expected,
        "len_lt": lambda: len(actual) < expected,
    }
    if not operations[matcher]():
        raise AssertionError(f"assertion failed: actual={actual!r} {matcher} expected={expected!r}")
