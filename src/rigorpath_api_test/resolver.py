from __future__ import annotations

import re
from typing import Any, Mapping


PLACEHOLDER_RE = re.compile(r"\$\{([^}]+)\}")


def resolve(value: Any, env: Mapping[str, str], cache: Mapping[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: resolve(item, env, cache) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, env, cache) for item in value]
    if not isinstance(value, str):
        return value

    full = PLACEHOLDER_RE.fullmatch(value)
    if full:
        return _lookup(full.group(1), env, cache)
    return PLACEHOLDER_RE.sub(lambda match: str(_lookup(match.group(1), env, cache)), value)


def _lookup(name: str, env: Mapping[str, str], cache: Mapping[str, Any]) -> Any:
    if name.startswith("cache."):
        key = name.removeprefix("cache.")
        if key not in cache:
            raise KeyError(f"missing captured value: {key}")
        return cache[key]
    if name not in env or env[name] == "":
        raise KeyError(f"missing required environment value: {name}")
    return env[name]
