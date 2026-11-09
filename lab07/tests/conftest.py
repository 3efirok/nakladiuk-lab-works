"""Shared fixtures of the test suite."""

import logging
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest
import yaml
from sqlalchemy.orm import Session, sessionmaker

from experiment_registry.domain.models import Experiment, ExperimentResult, Researcher
from experiment_registry.domain.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.domain.services import ExperimentService
from experiment_registry.domain.value_objects import Measurement

CSV_HEADER = "experiment_id,name,researcher,parameter,result,date\n"
VALID_ROWS = (
    "1,Thermal conductivity of Al alloy,Olena Kovalenko,temperature,293.4,2026-02-03\n"
    "1,Thermal conductivity of Al alloy,Olena Kovalenko,temperature,301.8,2026-02-10\n"
    "2,Gas compression test,Taras Hnatiuk,pressure,101.3,2026-02-05\n"
)


@pytest.fixture
def researcher() -> Researcher:
    return Researcher(1, "Olena", "Kovalenko", "o.kovalenko@lnu.edu.ua")


@pytest.fixture
def experiment(researcher: Researcher) -> Experiment:
    """Experiment with three temperature results."""
    item = Experiment(1, "Thermal conductivity of Al alloy", researcher, "temperature", "K")
    for result_id, value in enumerate((293.4, 297.1, 301.8), start=1):
        item.add_result(ExperimentResult(result_id, Measurement("temperature", value, "K"),
                                         date(2026, 2, result_id)))
    return item


@pytest.fixture
def experiment_service(researcher: Researcher) -> ExperimentService:
    """Service with real in-memory repositories (fakes) and two experiments."""
    service = ExperimentService(ExperimentRepository(), ResearcherRepository())
    service.register_researcher(researcher)
    service.register_researcher(Researcher(2, "Taras", "Hnatiuk", "t.hnatiuk@lnu.edu.ua"))
    service.create_experiment(1, "Thermal conductivity of Al alloy", 1, "temperature", "K")
    service.create_experiment(2, "Gas compression test", 2, "pressure", "kPa")
    return service


@pytest.fixture
def make_measurement() -> Callable[..., Measurement]:
    """Fixture factory: builds measurements with sensible defaults."""

    def factory(value: float = 300.0, parameter: str = "temperature", unit: str = "K") -> Measurement:
        return Measurement(parameter, value, unit)

    return factory


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "experiments.csv"
    path.write_text(CSV_HEADER + VALID_ROWS + "3,Broken result,Iryna Melnyk,voltage,wrong,2026-02-12\n",
                    encoding="utf-8")
    return path


@pytest.fixture
def config_data(csv_file: Path) -> dict[str, object]:
    """Raw configuration mapping pointing to files inside tmp_path."""
    return {
        "version": 1,
        "input": {"path": csv_file.name},
        "output": {"path": "output/experiments.json", "errors_path": "output/rejected.csv",
                   "create_dirs": True, "indent": 2},
        "validation": {"allowed_parameters": {"temperature": "K", "pressure": "kPa", "voltage": "V"},
                       "min_result": 0.0, "max_result": 10000.0},
        "processing": {"skip_invalid": True},
        "logging": {"level": "INFO", "file": "logs/importer.log"},
    }


@pytest.fixture
def config_file(tmp_path: Path, config_data: dict[str, object]) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config_data), encoding="utf-8")
    return path


@pytest.fixture
def importer_logger() -> Iterator[logging.Logger]:
    """Fixture with teardown: closes file handlers created by setup_logging()."""
    logger = logging.getLogger("experiment_registry.importer")
    yield logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


# ---------------------------------------------------------------- database (lab 7)
@pytest.fixture
def db_url(tmp_path: Path) -> str:
    """Separate SQLite file for every test - never the development database."""
    return f"sqlite:///{tmp_path / 'test_experiments.db'}"


@pytest.fixture
def session_factory(db_url: str) -> Iterator[sessionmaker[Session]]:
    from experiment_registry.persistence.database import create_db_engine, create_session_factory, init_db

    engine = create_db_engine(db_url)
    init_db(engine)
    yield create_session_factory(engine)
    engine.dispose()


@pytest.fixture
def db_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    yield session
    session.rollback()
    session.close()
