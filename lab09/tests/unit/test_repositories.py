import pytest

from experiment_registry.domain.models import Experiment, Researcher
from experiment_registry.domain.protocols import Identifiable
from experiment_registry.domain.repositories import ExperimentRepository, InMemoryRepository
from experiment_registry.exceptions import DuplicateExperimentError, ExperimentNotFoundError


def test_repository_add_get_and_contains(researcher: Researcher) -> None:
    repository: InMemoryRepository[Researcher] = InMemoryRepository()

    repository.add(researcher)

    assert repository.get(1) is researcher
    assert 1 in repository and 2 not in repository
    assert len(repository) == 1


def test_repository_rejects_duplicate_id(researcher: Researcher) -> None:
    repository: InMemoryRepository[Researcher] = InMemoryRepository()
    repository.add(researcher)

    with pytest.raises(DuplicateExperimentError):
        repository.add(researcher)


def test_missing_item_raises_not_found() -> None:
    with pytest.raises(ExperimentNotFoundError, match="id=42"):
        InMemoryRepository[Researcher]().get(42)


def test_remove_returns_item_and_deletes_it(researcher: Researcher) -> None:
    repository: InMemoryRepository[Researcher] = InMemoryRepository()
    repository.add(researcher)

    assert repository.remove(1) is researcher
    assert repository.list_all() == []


def test_experiment_repository_finds_by_researcher(experiment: Experiment) -> None:
    repository = ExperimentRepository()
    repository.add(experiment)

    assert repository.find_by_researcher("olena kovalenko") == [experiment]
    assert repository.find_by_researcher("Taras Hnatiuk") == []


def test_domain_entities_satisfy_identifiable_protocol(experiment: Experiment, researcher: Researcher) -> None:
    assert isinstance(experiment, Identifiable)
    assert isinstance(researcher, Identifiable)
