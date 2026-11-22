"""Command line: pc2dbt convert <xml> --out <dir> [--mapping NAME ...]"""
from __future__ import annotations

import argparse
import sys

from .project import write_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pc2dbt", description="Convert a PowerCenter mapping XML into a dbt project.")
    sub = parser.add_subparsers(dest="command", required=True)
    conv = sub.add_parser("convert", help="write a dbt project for the mappings in the XML")
    conv.add_argument("xml", help="PowerCenter XML export")
    conv.add_argument("--out", required=True, help="folder to write the dbt project into")
    conv.add_argument("--mapping", action="append", help="mapping to convert (repeat for several; default: all)")
    args = parser.parse_args(argv)

    report = write_project(args.xml, args.out, args.mapping)
    print(f"Wrote {len(report.models)} models with {len(report.flags)} flags to {args.out} (see flags.md).")
    for n in report.not_converted:  # decision Q18: say what was not converted, and exit with an error
        print(f"not converted: {n.folder}/{n.model}: {n.what} (L{n.line})", file=sys.stderr)
    if report.not_converted:
        print(f"{len(report.not_converted)} model(s) could not be converted; dbt will stop on them.", file=sys.stderr)
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
