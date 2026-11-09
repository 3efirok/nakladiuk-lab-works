"""Experiment 4: the same behaviour tested with a Mock and with a fake repository."""

from unittest.mock import Mock

from experiment_registry.domain.models import Experiment, Researcher
from experiment_registry.domain.repositories import ExperimentRepository, ResearcherRepository
from experiment_registry.domain.services import ExperimentService

OLENA = Researcher(1, "Olena", "Kovalenko", "o.kovalenko@lnu.edu.ua")


def test_find_by_researcher_with_mock() -> None:
    repository = Mock(spec=ExperimentRepository)
    repository.find_by_researcher.return_value = ["experiment #1"]
    service = ExperimentService(repository, Mock(spec=ResearcherRepository))

    assert service.find_by_researcher("Olena Kovalenko") == ["experiment #1"]
    repository.find_by_researcher.assert_called_once_with("Olena Kovalenko")  # interaction


def test_find_by_researcher_with_fake() -> None:
    repository = ExperimentRepository()  # real in-memory implementation used as a fake
    repository.add(Experiment(1, "Thermal conductivity", OLENA, "temperature", "K"))
    service = ExperimentService(repository, ResearcherRepository())

    found = service.find_by_researcher("olena kovalenko")

    assert [item.id for item in found] == [1]  # state
