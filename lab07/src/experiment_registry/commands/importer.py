"""Lab 5 scenario: reliable import / export driven by config.yaml."""

import sys
from dataclasses import replace
from pathlib import Path

from experiment_registry.exceptions import ConfigurationError, DataImportError, ExportError
from experiment_registry.importer.config import load_config
from experiment_registry.importer.logging_config import setup_logging
from experiment_registry.importer.services import ImportService

EXIT_OK = 0
EXIT_IMPORT_FAILED = 1
EXIT_CONFIG_ERROR = 2


def run_import(config_path: Path, strict: bool | None = None) -> int:
    """Run the import; return a process exit code instead of crashing with a traceback."""
    try:
        config = load_config(config_path)
    except ConfigurationError as error:
        print(f"CRITICAL: configuration error: {error}", file=sys.stderr)
        if error.__cause__ is not None:
            print(f"  caused by {type(error.__cause__).__name__}: {error.__cause__}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    if strict is not None:
        config = replace(config, processing=replace(config.processing, skip_invalid=not strict))
    logger = setup_logging(config.logging)
    mode = "tolerant" if config.processing.skip_invalid else "strict"
    print(f"Config: {config_path} | mode: {mode} | input: {config.input_path}")

    service = ImportService(config, logger)
    try:
        stats = service.run()
    except (DataImportError, ExportError) as error:
        logger.critical("Import failed: %s", error)
        print(f"CRITICAL: {error}", file=sys.stderr)
        if error.__cause__ is not None:
            print(f"  caused by {type(error.__cause__).__name__}: {error.__cause__}", file=sys.stderr)
        print(f"Statistics before abort: {service.stats.as_dict()}")
        return EXIT_IMPORT_FAILED

    print(f"Processed: {stats.processed} | valid: {stats.valid} | invalid: {stats.invalid} | "
          f"filtered out: {stats.filtered_out} | exported: {stats.exported}")
    if stats.errors_by_field:
        print(f"Invalid records by field: {dict(stats.errors_by_field)}")
    print(f"Output: {config.output_path}")
    if config.errors_path is not None and service.rejected:
        print(f"Rejected records: {config.errors_path}")
    print(f"Log: {config.logging.file}")
    return EXIT_OK
