# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №5 — обробка помилок, файли та серіалізація.

Варіант 15 — імпорт та експорт результатів наукових експериментів.
Поля CSV: `experiment_id, name, researcher, parameter, result, date`.

## Що додано в лабораторній №5

Пакет `experiment_registry.importer`:

- `config.py` — завантаження `config.yaml` (PyYAML), typed dataclasses, валідація,
  перевизначення через змінні середовища `EXPERIMENTS_INPUT`, `EXPERIMENTS_OUTPUT`,
  `EXPERIMENTS_SKIP_INVALID`, `EXPERIMENTS_LOG_LEVEL`;
- `readers.py` — потокове читання CSV / JSON Lines, вибір формату за розширенням;
- `validators.py` — перевірка ID, назви, дослідника, параметра (список із YAML), числового
  результату й дати; exception chaining (`raise ... from error`);
- `exporters.py` — `AtomicWriter` (власний context manager: тимчасовий файл + `os.replace`),
  JSON-експорт із власним encoder, CSV із відхиленими записами;
- `logging_config.py` — лог-файл з ротацією (`RotatingFileHandler`);
- `services.py` — `ImportService`: strict/tolerant режим, статистика, контекстний менеджер `log_stage`.

Ієрархія винятків (`exceptions.py`):

```text
ExperimentError
├── ExperimentValidationError ── IncompatibleMeasurementError
├── ConfigurationError
├── DataImportError ── RecordValidationError (line, field, value)
└── ExportError
```

## Запуск

```bash
python -m pip install -e ".[dev]"
experiment-registry import                 # режим з config.yaml (tolerant)
experiment-registry import --strict        # перша помилка зупиняє імпорт
EXPERIMENTS_SKIP_INVALID=false experiment-registry import
python benchmarks/import_experiments.py    # експерименти 1-5
```

Коди завершення: `0` — успіх, `1` — імпорт перервано, `2` — помилка конфігурації.
Результати: `output/experiments.json`, `output/rejected.csv`, журнал `logs/importer.log`.

## Автор

Накладюк Володимир, група ФеП-32
