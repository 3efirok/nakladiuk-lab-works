"""Console entry point: dispatches sub-commands of the application."""

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="experiment-registry",
        description="Registry of scientific experiment results.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("demo", help="lab 1 demo scenario (default)")
    sub.add_parser("menu", help="interactive console menu")
    analyze = sub.add_parser("analyze", help="data-structure analysis of experiments")
    analyze.add_argument("--range", nargs=2, type=float, default=(250.0, 350.0),
                         metavar=("LOW", "HIGH"), help="result range for filtering")
    analyze.add_argument("--researcher", default="Olena Kovalenko")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command in (None, "demo"):
        from experiment_registry.commands.demo import create_demo_experiments, run_demo

        run_demo(create_demo_experiments())
    elif args.command == "menu":
        from experiment_registry.commands.demo import create_demo_experiments, run_menu

        run_menu(create_demo_experiments())
    elif args.command == "analyze":
        from experiment_registry.commands.analyze import run_analysis

        run_analysis(args.researcher, *args.range)


if __name__ == "__main__":
    main()
