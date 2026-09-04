from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

import yaml


AUTO_ID_RE = re.compile(r"^AUTO-\d+$")
REF_PATTERNS = {
    "requirements": re.compile(r"^REQ-\d+$"),
    "business_rules": re.compile(r"^BR-\d+$"),
    "questions": re.compile(r"^Q-\d+$"),
    "risks": re.compile(r"^RISK-\d+$"),
    "test_points": re.compile(r"^TP-\d+$"),
    "test_cases": re.compile(r"^TC-\d+$"),
    "data_rows": re.compile(r"^DATA-\d+$"),
}
ASSERTION_TYPES = {
    "requirement",
    "business_rule",
    "contract",
    "risk_derived",
    "hypothesis",
}
MATCHERS = {
    "eq",
    "ne",
    "lt",
    "lte",
    "gt",
    "gte",
    "contains",
    "len_eq",
    "len_gt",
    "len_lt",
}
TARGETS = {"status", "jsonpath", "duration_ms", "text"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
PLACEHOLDER_RE = re.compile(r"\$\{([^}]+)\}")


class CaseContractError(ValueError):
    pass


def _files(paths: Iterable[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(path.rglob("*.yaml")))
            found.extend(sorted(path.rglob("*.yml")))
        else:
            found.append(path)
    return sorted(set(found))


def _unknown(value: dict[str, Any], allowed: set[str], where: str, errors: list[str]) -> None:
    for key in sorted(set(value) - allowed):
        errors.append(f"{where}: unknown field {key!r}")


def _refs(source: Any, where: str, errors: list[str]) -> None:
    if not isinstance(source, dict):
        errors.append(f"{where}: source must be a mapping")
        return
    _unknown(source, set(REF_PATTERNS), where, errors)
    for field, pattern in REF_PATTERNS.items():
        values = source.get(field, [])
        if not isinstance(values, list) or any(not pattern.fullmatch(str(v)) for v in values):
            errors.append(f"{where}.{field}: invalid reference list")
    if not source.get("test_points") or not source.get("test_cases"):
        errors.append(f"{where}: test_points and test_cases are required")


def _request(request: Any, where: str, errors: list[str]) -> None:
    if not isinstance(request, dict):
        errors.append(f"{where}: request must be a mapping")
        return
    allowed = {"method", "path", "headers", "query", "json", "timeout_seconds"}
    _unknown(request, allowed, where, errors)
    method = str(request.get("method", "")).upper()
    if method not in METHODS:
        errors.append(f"{where}.method: must be one of {sorted(METHODS)}")
    path = request.get("path")
    if not isinstance(path, str) or not path.startswith("/"):
        errors.append(f"{where}.path: must start with '/'")
    if "query" in request and not isinstance(request["query"], dict):
        errors.append(f"{where}.query: must be a mapping")
    if "headers" in request and not isinstance(request["headers"], dict):
        errors.append(f"{where}.headers: must be a mapping")


def _assertions(assertions: Any, where: str, errors: list[str]) -> None:
    if not isinstance(assertions, list) or not assertions:
        errors.append(f"{where}: at least one assertion is required")
        return
    for index, item in enumerate(assertions, 1):
        here = f"{where}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{here}: assertion must be a mapping")
            continue
        _unknown(item, {"type", "source", "target", "path", "matcher", "expected"}, here, errors)
        assertion_type = item.get("type")
        if assertion_type not in ASSERTION_TYPES:
            errors.append(f"{here}.type: invalid assertion type")
        source = str(item.get("source", "")).strip()
        if not source:
            errors.append(f"{here}.source: exact source is required")
        if assertion_type == "requirement" and not re.search(r"\bREQ-\d+\b", source):
            errors.append(f"{here}.source: requirement assertion requires REQ-###")
        if assertion_type == "business_rule" and not re.search(r"\bBR-\d+\b", source):
            errors.append(f"{here}.source: business_rule assertion requires BR-###")
        if assertion_type in {"risk_derived", "hypothesis"} and not re.search(
            r"\b(?:RISK|TP|Q)-\d+\b", source
        ):
            errors.append(f"{here}.source: risk-derived assertion requires RISK/TP/Q reference")
        target = item.get("target")
        if target not in TARGETS:
            errors.append(f"{here}.target: invalid target")
        if target == "jsonpath" and not str(item.get("path", "")).startswith("$"):
            errors.append(f"{here}.path: jsonpath assertion requires '$' path")
        matcher = item.get("matcher")
        if matcher not in MATCHERS:
            errors.append(f"{here}.matcher: invalid matcher")
        if "expected" not in item:
            errors.append(f"{here}.expected: required")
        if matcher == "contains" and item.get("expected") == "":
            errors.append(f"{here}: contains empty string is a tautological assertion")


def _captures(captures: Any, where: str, errors: list[str]) -> None:
    if captures is None:
        return
    if not isinstance(captures, list):
        errors.append(f"{where}: capture must be a list")
        return
    seen: set[str] = set()
    for index, item in enumerate(captures, 1):
        here = f"{where}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{here}: capture must be a mapping")
            continue
        _unknown(item, {"name", "path"}, here, errors)
        name = str(item.get("name", ""))
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            errors.append(f"{here}.name: must be lower_snake_case")
        elif name in seen:
            errors.append(f"{here}.name: duplicate {name}")
        seen.add(name)
        if not str(item.get("path", "")).startswith("$"):
            errors.append(f"{here}.path: must be a JSONPath")


def validate_suite(data: Any, source: str = "<memory>") -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"{source}: suite must be a mapping"]
    _unknown(data, {"schema_version", "suite", "required_env", "cases"}, source, errors)
    if data.get("schema_version") != 1:
        errors.append(f"{source}.schema_version: must be 1")
    required_env = data.get("required_env", [])
    if not isinstance(required_env, list) or any(not isinstance(v, str) or not v for v in required_env):
        errors.append(f"{source}.required_env: must be a string list")
        required_env = []
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append(f"{source}.cases: at least one case is required")
        return errors
    seen: set[str] = set()
    for index, case in enumerate(cases, 1):
        where = f"{source}.cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{where}: case must be a mapping")
            continue
        _unknown(
            case,
            {"id", "title", "source", "request", "assertions", "capture", "cleanup", "side_effect", "enabled"},
            where,
            errors,
        )
        case_id = str(case.get("id", ""))
        if not AUTO_ID_RE.fullmatch(case_id):
            errors.append(f"{where}.id: must be AUTO-###")
        elif case_id in seen:
            errors.append(f"{where}.id: duplicate {case_id}")
        seen.add(case_id)
        if not str(case.get("title", "")).strip():
            errors.append(f"{where}.title: required")
        _refs(case.get("source"), f"{where}.source", errors)
        _request(case.get("request"), f"{where}.request", errors)
        _assertions(case.get("assertions"), f"{where}.assertions", errors)
        _captures(case.get("capture"), f"{where}.capture", errors)
        if "side_effect" not in case:
            errors.append(f"{where}.side_effect: explicit declaration is required")
        side_effect = case.get("side_effect", "none")
        if side_effect not in {"none", "isolated", "cleanup"}:
            errors.append(f"{where}.side_effect: must be none, isolated, or cleanup")
        if side_effect == "cleanup" and not isinstance(case.get("cleanup"), dict):
            errors.append(f"{where}.cleanup: required when side_effect is cleanup")
        if "cleanup" in case:
            _request(case["cleanup"], f"{where}.cleanup", errors)
        declared = set(required_env)
        for name in PLACEHOLDER_RE.findall(yaml.safe_dump(case, allow_unicode=True)):
            if not name.startswith("cache.") and name not in declared:
                errors.append(f"{where}: placeholder {name!r} is not listed in required_env")
    return errors


def load_suites(paths: Iterable[Path]) -> list[dict[str, Any]]:
    suites: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_auto: dict[str, str] = {}
    for path in _files(paths):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            errors.append(f"{path}: {exc}")
            continue
        errors.extend(validate_suite(data, str(path)))
        if isinstance(data, dict):
            suites.append(data)
            for case in data.get("cases", []) if isinstance(data.get("cases"), list) else []:
                if isinstance(case, dict) and AUTO_ID_RE.fullmatch(str(case.get("id", ""))):
                    case_id = str(case["id"])
                    if case_id in seen_auto:
                        errors.append(f"{path}: duplicate {case_id}; first defined in {seen_auto[case_id]}")
                    seen_auto[case_id] = str(path)
    if not suites and not errors:
        errors.append("no YAML case files found")
    if errors:
        raise CaseContractError("\n".join(errors))
    return suites


def iter_cases(suites: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [case for suite in suites for case in suite["cases"] if case.get("enabled", True)]


def validate_paths(paths: Iterable[Path]) -> list[str]:
    try:
        load_suites(paths)
    except CaseContractError as exc:
        return str(exc).splitlines()
    return []
