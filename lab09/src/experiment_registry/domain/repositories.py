"""Generic in-memory repository."""

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from experiment_registry.domain.models import Experiment, Researcher
from experiment_registry.domain.protocols import Identifiable
from experiment_registry.exceptions import DuplicateExperimentError, ExperimentNotFoundError

T = TypeVar("T", bound=Identifiable)


class InMemoryRepository(Generic[T]):
    """Stores objects of one type by their `id` (dict index => O(1) access)."""

    def __init__(self) -> None:
        self._items: dict[int, T] = {}

    def add(self, item: T) -> None:
        if item.id in self._items:
            raise DuplicateExperimentError(f"Object with id={item.id} already exists.")
        self._items[item.id] = item

    def get(self, item_id: int) -> T:
        try:
            return self._items[item_id]
        except KeyError:
            raise ExperimentNotFoundError(f"Object with id={item_id} not found.") from None

    def remove(self, item_id: int) -> T:
        item = self.get(item_id)
        del self._items[item_id]
        return item

    def list_all(self) -> list[T]:
        return list(self._items.values())

    def find(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self._items.values() if predicate(item)]

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __contains__(self, item_id: object) -> bool:
        return item_id in self._items


class ExperimentRepository(InMemoryRepository[Experiment]):
    """Repository with experiment-specific queries."""

    def find_by_researcher(self, researcher_name: str) -> list[Experiment]:
        wanted = researcher_name.strip().lower()
        return self.find(lambda item: item.researcher.full_name.lower() == wanted)


class ResearcherRepository(InMemoryRepository[Researcher]):
    def find_by_name(self, full_name: str) -> Researcher | None:
        matches = self.find(lambda item: item.full_name.lower() == full_name.strip().lower())
        return matches[0] if matches else None
