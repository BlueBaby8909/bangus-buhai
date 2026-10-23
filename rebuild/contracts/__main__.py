"""Explicit schema export, or a read-only schema/fixture check."""

import argparse
import sys

from .artifacts import check_artifacts, export_schemas, schema_documents


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "export-schemas"))
    arguments = parser.parse_args()
    if arguments.command == "export-schemas":
        export_schemas()
        print(f"Exported {len(schema_documents())} v1 schemas. No fixture or model files changed.")
        return 0
    try:
        count, failures = check_artifacts()
    except (OSError, ValueError, KeyError, TypeError):
        print("Contract check failed: unreadable or invalid local artifacts.", file=sys.stderr)
        return 1
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print(f"PASS: {count} fixture cases and {len(schema_documents())} schema snapshots. No contract artifacts written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
