from pathlib import Path

import pytest
import yaml

from experiment_registry.exceptions import ConfigurationError
from experiment_registry.importer.config import apply_env_overrides, load_config


def write_config(path: Path, data: object) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_load_config_builds_typed_configuration(config_file: Path) -> None:
    config = load_config(config_file, env={})

    assert config.input_path == config_file.parent / "experiments.csv"
    assert config.validation.allowed_parameters["pressure"] == "kPa"
    assert config.processing.skip_invalid is True
    assert config.logging.level == "INFO"


def test_missing_config_file_raises_configuration_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found") as exc_info:
        load_config(tmp_path / "missing.yaml", env={})

    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


def test_invalid_yaml_raises_configuration_error(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("version: 1\ninput: [path: data\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_config(path, env={})


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.pop("input"), "Missing required section 'input'"),
        (lambda d: d["validation"].update(min_result=20000), "must be less than"),
        (lambda d: d["validation"].update(allowed_parameters={}), "must not be empty"),
        (lambda d: d["input"].update(path="missing.csv"), "Input file not found"),
        (lambda d: d["output"].update(path="no_dir/out.json", create_dirs=False), "Output directory"),
        (lambda d: d.update(version=2), "Unsupported config version"),
        (lambda d: d["logging"].update(level="LOUD"), "Unknown log level"),
    ],
    ids=["no-input", "min>max", "no-parameters", "no-input-file", "no-output-dir", "version", "log-level"],
)
def test_invalid_configuration_is_rejected(tmp_path: Path, config_data: dict, change, message: str) -> None:
    change(config_data)

    with pytest.raises(ConfigurationError, match=message):
        load_config(write_config(tmp_path / "config.yaml", config_data), env={})


def test_environment_variable_overrides_yaml(config_file: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPERIMENTS_SKIP_INVALID", "false")
    monkeypatch.setenv("EXPERIMENTS_LOG_LEVEL", "debug")

    config = load_config(config_file)

    assert config.processing.skip_invalid is False
    assert config.logging.level == "DEBUG"


def test_without_environment_variables_yaml_values_are_used(config_file: Path,
                                                             monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPERIMENTS_SKIP_INVALID", raising=False)

    assert load_config(config_file).processing.skip_invalid is True


def test_invalid_boolean_in_environment_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="boolean"):
        apply_env_overrides({}, {"EXPERIMENTS_SKIP_INVALID": "maybe"})


@pytest.mark.parametrize(("raw", "expected"), [(False, False), ("false", False), ("no", False),
                                               (True, True), ("yes", True)])
def test_skip_invalid_accepts_yaml_booleans_and_strings(tmp_path: Path, config_data: dict,
                                                        raw: object, expected: bool) -> None:
    """A quoted "false" in YAML is a string; it must not silently enable tolerant mode."""
    config_data["processing"] = {"skip_invalid": raw}

    config = load_config(write_config(tmp_path / "config.yaml", config_data), env={})

    assert config.processing.skip_invalid is expected


def test_unrecognized_boolean_in_yaml_is_rejected(tmp_path: Path, config_data: dict) -> None:
    config_data["output"]["create_dirs"] = "sometimes"

    with pytest.raises(ConfigurationError, match="boolean"):
        load_config(write_config(tmp_path / "config.yaml", config_data), env={})
