# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №4 — професійне ООП та система типів Python.

Варіант 15 — система обліку результатів наукових експериментів.

## Доменна модель (`experiment_registry.domain`)

| Модуль | Вміст |
|--------|-------|
| `value_objects.py` | `Measurement` (frozen dataclass, `total_ordering`, `__sub__`), `ResultRange` (`__contains__`) |
| `models.py` | `Person` → `Researcher` (наслідування, properties), `ExperimentResult` (dataclass), `Experiment` (композиція результатів), `ExperimentSeries` (власна колекція) |
| `protocols.py` | `Identifiable` (`runtime_checkable`), `ReportExporter`, `ReportSink` |
| `dto.py` | `ExperimentPayload`, `AnalysisReport` (TypedDict) |
| `repositories.py` | `InMemoryRepository[T]` (Generic + bound TypeVar), `ExperimentRepository`, `ResearcherRepository` |
| `strategies.py` | ABC `AnalysisStrategy` і стратегії average / minimum / maximum / std_dev |
| `exporters.py` | `JsonReportExporter`, `TextReportExporter`, `ConsoleSink`, `MemorySink` |
| `services.py` | `ExperimentService`, `ReportingService` (dependency injection) |
| `processing.py` | порівняння inheritance і composition |

## Запуск

```bash
python -m pip install -e ".[dev]"
experiment-registry domain
mypy            # налаштування в [tool.mypy], strict = true
```

Попередні підкоманди (`demo`, `menu`, `analyze`, `iterators`, `stream`, `generate`) збережено.

## Автор

Накладюк Володимир, група ФеП-32
