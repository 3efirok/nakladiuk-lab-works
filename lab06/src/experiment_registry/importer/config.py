"""Loading and validation of the YAML configuration."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from experiment_registry.exceptions import ConfigurationError

SCHEMA_VERSION = 1
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class ValidationConfig:
    allowed_parameters: dict[str, str]  # parameter -> unit
    min_result: float
    max_result: float


@dataclass(frozen=True)
class ProcessingConfig:
    skip_invalid: bool = True
    researcher: str | None = None
    result_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file: Path = Path("logs/importer.log")
    max_bytes: int = 1_000_000
    backup_count: int = 3


@dataclass(frozen=True)
class AppConfig:
    input_path: Path
    output_path: Path
    errors_path: Path | None
    create_dirs: bool
    indent: int
    validation: ValidationConfig
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _section(data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    try:
        value = data[key]
    except KeyError as error:
        raise ConfigurationError(f"Missing required section '{key}'.") from error
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"Section '{key}' must be a mapping.")
    return value


def _to_bool(value: object, source: str) -> bool:
    """Strict boolean parsing: bool("false") would be True, so strings are mapped explicitly."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.strip().lower() in {"1", "true", "yes", "on"}:
            return True
        if value.strip().lower() in {"0", "false", "no", "off"}:
            return False
    raise ConfigurationError(f"Invalid boolean value for {source}: {value!r}.")


def _env_bool(value: str) -> bool:
    return _to_bool(value, "environment variable")


def apply_env_overrides(data: dict[str, Any], env: Mapping[str, str]) -> dict[str, Any]:
    """Environment variables override YAML values (EXPERIMENTS_INPUT, ...)."""
    if "EXPERIMENTS_INPUT" in env:
        data.setdefault("input", {})["path"] = env["EXPERIMENTS_INPUT"]
    if "EXPERIMENTS_OUTPUT" in env:
        data.setdefault("output", {})["path"] = env["EXPERIMENTS_OUTPUT"]
    if "EXPERIMENTS_SKIP_INVALID" in env:
        data.setdefault("processing", {})["skip_invalid"] = _env_bool(env["EXPERIMENTS_SKIP_INVALID"])
    if "EXPERIMENTS_LOG_LEVEL" in env:
        data.setdefault("logging", {})["level"] = env["EXPERIMENTS_LOG_LEVEL"]
    return data


def parse_config(data: Mapping[str, Any], base_dir: Path = Path(".")) -> AppConfig:
    """Build a typed AppConfig from a raw mapping and validate it (fail-fast)."""
    if data.get("version") != SCHEMA_VERSION:
        raise ConfigurationError(f"Unsupported config version {data.get('version')!r}, expected {SCHEMA_VERSION}.")
    input_section = _section(data, "input")
    output_section = _section(data, "output")
    validation_section = _section(data, "validation")
    processing_section = data.get("processing", {}) or {}
    logging_section = data.get("logging", {}) or {}

    try:
        input_path = base_dir / str(input_section["path"])
        output_path = base_dir / str(output_section["path"])
        allowed = {str(k): str(v) for k, v in dict(validation_section["allowed_parameters"]).items()}
        min_result = float(validation_section["min_result"])
        max_result = float(validation_section["max_result"])
    except KeyError as error:
        raise ConfigurationError(f"Missing required key {error}.") from error
    except (TypeError, ValueError) as error:
        raise ConfigurationError(f"Invalid value in configuration: {error}.") from error

    errors_raw = output_section.get("errors_path")
    raw_range = processing_section.get("result_range")
    result_range = None
    if raw_range is not None:
        if not isinstance(raw_range, list) or len(raw_range) != 2:
            raise ConfigurationError("processing.result_range must be a list [low, high].")
        result_range = (float(raw_range[0]), float(raw_range[1]))

    config = AppConfig(
        input_path=input_path,
        output_path=output_path,
        errors_path=base_dir / str(errors_raw) if errors_raw else None,
        create_dirs=_to_bool(output_section.get("create_dirs", False), "output.create_dirs"),
        indent=int(output_section.get("indent", 2)),
        validation=ValidationConfig(allowed, min_result, max_result),
        processing=ProcessingConfig(
            skip_invalid=_to_bool(processing_section.get("skip_invalid", True), "processing.skip_invalid"),
            researcher=processing_section.get("researcher"),
            result_range=result_range,
        ),
        logging=LoggingConfig(
            level=str(logging_section.get("level", "INFO")).upper(),
            file=base_dir / str(logging_section.get("file", "logs/importer.log")),
            max_bytes=int(logging_section.get("max_bytes", 1_000_000)),
            backup_count=int(logging_section.get("backup_count", 3)),
        ),
    )
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    v = config.validation
    if not v.allowed_parameters:
        raise ConfigurationError("validation.allowed_parameters must not be empty.")
    if v.min_result >= v.max_result:
        raise ConfigurationError(f"min_result ({v.min_result}) must be less than max_result ({v.max_result}).")
    if config.processing.result_range is not None:
        low, high = config.processing.result_range
        if low > high:
            raise ConfigurationError(f"processing.result_range: {low} > {high}.")
    if config.logging.level not in LOG_LEVELS:
        raise ConfigurationError(f"Unknown log level {config.logging.level!r}.")
    if config.indent < 0:
        raise ConfigurationError("output.indent must be >= 0.")
    if not config.input_path.is_file():
        raise ConfigurationError(f"Input file not found: {config.input_path}.")
    if not config.create_dirs and not config.output_path.parent.is_dir():
        raise ConfigurationError(f"Output directory does not exist: {config.output_path.parent}.")


def load_config(path: Path, env: Mapping[str, str] | None = None) -> AppConfig:
    """Read YAML, apply environment overrides and return a validated configuration."""
    try:
        with path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except FileNotFoundError as error:
        raise ConfigurationError(f"Configuration file not found: {path}.") from error
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML in {path}: {error}.") from error
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuration root must be a mapping, got {type(data).__name__}.")
    data = apply_env_overrides(data, os.environ if env is None else env)
    return parse_config(data, base_dir=path.parent)
