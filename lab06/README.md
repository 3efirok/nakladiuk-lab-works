# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №6 — автоматизоване тестування Python-програм.

Варіант 15 — система обліку результатів наукових експериментів.

## Test suite

```text
tests/
├── conftest.py                     # спільні fixtures (у т.ч. factory та fixture з yield)
├── unit/
│   ├── test_value_objects.py       # Measurement, ResultRange
│   ├── test_models.py              # Researcher, Experiment, ExperimentResult, ExperimentSeries
│   ├── test_strategies.py          # average / min / max / std_dev
│   ├── test_services.py            # ExperimentService, ReportingService (Mock, side_effect)
│   ├── test_repositories.py        # generic repository
│   ├── test_validators.py          # валідація parameter / value / date
│   ├── test_configuration.py       # YAML, monkeypatch для змінних середовища
│   ├── test_readers.py             # CSV / JSON Lines
│   ├── test_exporters.py           # JSON export, atomic output (tmp_path)
│   ├── test_async_source.py        # AsyncMock, Semaphore
│   ├── test_core_services.py       # ядро лабораторних 1-2
│   └── test_streaming.py           # потоковий конвеєр лабораторної 3
└── integration/
    ├── test_import_pipeline.py     # config -> CSV -> JSON -> log
    ├── test_experiment_pipeline.py # async source -> service -> report -> файл
    └── test_application_flow.py    # CLI end-to-end, коди завершення, меню
```

Каталог `experiments/` містить код експериментів лабораторної (слабкі/сильні тести,
coverage без assertions, branch coverage, Mock vs fake, flaky test, ізоляція tmp_path).
Він не входить до основного запуску (`testpaths = ["tests"]`).

## Запуск

```bash
python -m pip install -e ".[dev]"
pytest -v --cov --cov-branch --cov-report=term-missing --cov-report=html
pytest -m "not integration"       # лише unit tests
pytest -m integration             # лише integration tests
mypy
```

Мінімальне покриття задано в `pyproject.toml` (`fail_under = 80`).

## Автор

Накладюк Володимир, група ФеП-32
