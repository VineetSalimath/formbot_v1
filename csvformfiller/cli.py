from __future__ import annotations

import argparse

from .data import load_and_validate
from .models import PacingConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="csvformfiller",
        description=(
            "Fill Microsoft Forms from CSV data using explicit YAML mappings."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Interactively inspect visible Microsoft Forms questions.",
    )
    inspect_parser.add_argument("--url", required=True)
    inspect_parser.add_argument("--output", default="form_schema.json")

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate CSV headers against a mapping file.",
    )
    validate_parser.add_argument("--data", required=True)
    validate_parser.add_argument("--mapping", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Fill mapped rows. Dry-run is the default.",
    )
    run_parser.add_argument("--url", required=True)
    run_parser.add_argument("--data", required=True)
    run_parser.add_argument("--mapping", required=True)
    run_parser.add_argument("--id-column", default=None)
    run_parser.add_argument("--limit", type=int, default=None)
    run_parser.add_argument("--submit", action="store_true")
    run_parser.add_argument("--confirm-authorized", action="store_true")
    run_parser.add_argument("--page-delay-min", type=float, default=0.5)
    run_parser.add_argument("--page-delay-max", type=float, default=1.5)
    run_parser.add_argument("--row-delay-min", type=float, default=1.0)
    run_parser.add_argument("--row-delay-max", type=float, default=3.0)
    run_parser.add_argument("--log-file", default="submission_log.csv")
    run_parser.add_argument("--screenshot-dir", default="screenshots")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "inspect":
        from .inspect import inspect_form

        inspect_form(args.url, args.output)
        return

    mapping, rows = load_and_validate(args.data, args.mapping)

    if args.command == "validate":
        print(
            f"OK: {len(rows)} CSV row(s); "
            f"{len(mapping.required_columns)} mapped column(s)."
        )
        return

    if args.submit and not args.confirm_authorized:
        parser.error(
            "--submit requires --confirm-authorized. Only automate forms you "
            "own or have permission to submit to."
        )

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    pacing = PacingConfig(
        page_delay_min=args.page_delay_min,
        page_delay_max=args.page_delay_max,
        row_delay_min=args.row_delay_min,
        row_delay_max=args.row_delay_max,
    )

    from .runner import run_rows

    run_rows(
        url=args.url,
        rows=rows,
        mapping=mapping,
        submit=args.submit,
        id_column=args.id_column,
        limit=args.limit,
        pacing=pacing,
        log_file=args.log_file,
        screenshot_dir=args.screenshot_dir,
    )


if __name__ == "__main__":
    main()
