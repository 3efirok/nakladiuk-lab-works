"""Console entry point: dispatches sub-commands of the application."""

import argparse
from collections.abc import Sequence
from pathlib import Path


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

    sub.add_parser("iterators", help="iterator protocol and generator examples")
    stream = sub.add_parser("stream", help="lazy streaming pipeline over a CSV file")
    stream.add_argument("path", type=Path)
    stream.add_argument("--researcher")
    stream.add_argument("--parameter")
    stream.add_argument("--range", nargs=2, type=float, metavar=("LOW", "HIGH"))
    stream.add_argument("--first", type=int, default=5, help="show first N records")
    stream.add_argument("--batch", type=int, default=1000, help="batch size")
    generate = sub.add_parser("generate", help="generate a large CSV test file")
    generate.add_argument("path", type=Path)
    generate.add_argument("--count", type=int, default=100_000)
    generate.add_argument("--invalid-ratio", type=float, default=0.01)

    sub.add_parser("domain", help="typed object model and reporting services")
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
    elif args.command == "iterators":
        from experiment_registry.commands.stream import run_iterators_demo

        run_iterators_demo()
    elif args.command == "stream":
        from experiment_registry.commands.stream import run_stream

        low, high = args.range if args.range else (None, None)
        run_stream(args.path, args.researcher, args.parameter, low, high, args.first, args.batch)
    elif args.command == "generate":
        from experiment_registry.commands.stream import run_generate

        run_generate(args.path, args.count, args.invalid_ratio)
    elif args.command == "domain":
        from experiment_registry.commands.domain import run_domain_demo

        run_domain_demo()


if __name__ == "__main__":
    main()
