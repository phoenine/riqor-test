from __future__ import annotations

import argparse
from pathlib import Path

from .validation import validate_paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rigorpath-api-test")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args(argv)
    errors = validate_paths(args.paths)
    if errors:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
