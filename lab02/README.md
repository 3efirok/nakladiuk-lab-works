# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №2 — структури даних та функціональна декомпозиція.

Варіант 15 — аналіз результатів наукових експериментів
(назва, дослідник, параметр, результат, дата).

## Що додано в лабораторній №2

- `data.py` — вхідні дані як кортежі (`tuple`) та генератор великих наборів даних;
- `processors.py` — унікальні дослідники (`set`), індекси за ID і назвою (`dict`),
  пошук, універсальні фільтр і сортування, групування (`defaultdict`), `Counter`, pipeline;
- `analytics.py` — середнє, мінімум/максимум, рейтинг, статистика за дослідниками,
  функції з `*args` і `**kwargs`, closures (`make_range_filter`, `make_counter`);
- `decorators.py` — `measure_time`, параметризований `record_operation` з історією у `deque`;
- `commands/` — підкоманди консольного застосунку;
- `benchmarks/benchmark_search.py` — порівняння пошуку в `list` і `dict`.

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Запуск

```bash
experiment-registry demo            # сценарій лабораторної №1
experiment-registry menu            # консольне меню
experiment-registry analyze         # аналіз структур даних (лабораторна №2)
experiment-registry analyze --researcher "Taras Hnatiuk" --range 0 120
python benchmarks/benchmark_search.py
```

## Складність основних операцій

| Операція | Структура | Складність |
|----------|-----------|------------|
| пошук за ID | `list` | O(n) |
| побудова індексу | `dict` comprehension | O(n) |
| пошук за ключем | `dict.get` | O(1) у середньому |
| перевірка дослідника | `set` | O(1) у середньому |
| групування | `defaultdict(list)` | O(n) |
| рейтинг | `sorted` | O(n log n) |

## Структура проєкту

```text
lab02/
├── benchmarks/benchmark_search.py
├── pyproject.toml
├── README.md
└── src/experiment_registry/
    ├── __init__.py
    ├── analytics.py
    ├── commands/ (demo.py, analyze.py)
    ├── config.py
    ├── data.py
    ├── decorators.py
    ├── exceptions.py
    ├── main.py
    ├── models.py
    ├── processors.py
    └── services.py
```

## Автор

Накладюк Володимир, група ФеП-32
