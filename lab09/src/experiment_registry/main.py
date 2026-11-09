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

    imp = sub.add_parser("import", help="reliable CSV import and JSON export (config.yaml)")
    imp.add_argument("--config", type=Path, default=Path("config.yaml"))
    mode = imp.add_mutually_exclusive_group()
    mode.add_argument("--strict", dest="strict", action="store_true", default=None,
                      help="abort on the first invalid record")
    mode.add_argument("--tolerant", dest="strict", action="store_false",
                      help="skip and log invalid records")

    db = sub.add_parser("db", help="persistence layer demo (SQLite + SQLAlchemy)")
    db.add_argument("--url", default=None, help="database URL (default: $DATABASE_URL or sqlite:///experiments.db)")

    serve = sub.add_parser("serve", help="run the REST API with uvicorn")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    client = sub.add_parser("api-client", help="query API statistics concurrently (httpx)")
    client.add_argument("--base-url", default="http://127.0.0.1:8000")
    client.add_argument("--researchers", type=int, nargs="+", default=[1, 2, 3])
    client.add_argument("--timeout", type=float, default=2.0)
    client.add_argument("--retries", type=int, default=3)
    client.add_argument("--concurrency", type=int, default=4)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run a sub-command and return the process exit code."""
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
    elif args.command == "import":
        from experiment_registry.commands.importer import run_import

        return run_import(args.config, args.strict)
    elif args.command == "db":
        from experiment_registry.commands.db import run_db_demo
        from experiment_registry.persistence.database import get_database_url

        return run_db_demo(args.url or get_database_url())
    elif args.command == "serve":
        from experiment_registry.commands.api_client import run_server

        return run_server(args.host, args.port)
    elif args.command == "api-client":
        from experiment_registry.commands.api_client import run_api_client

        return run_api_client(args.base_url, args.researchers, args.timeout, args.retries, args.concurrency)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
