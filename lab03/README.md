# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №3 — ітератори, генератори та потокова обробка даних.

Варіант 15 — потокова обробка результатів наукових експериментів.
Формат вхідного CSV: `experiment_id,name,researcher,parameter,result,date`.

## Що додано в лабораторній №3

Пакет `experiment_registry.streaming`:

- `iterators.py` — власні iterator classes (`ExperimentRecordIterator`, `ResultSeries`),
  рекурсивний генератор `flatten` з `yield from`, нескінченний генератор `experiment_ids`;
- `readers.py` — потокове читання файлу рядок за рядком, об'єднання файлів через `chain`;
- `parsers.py` — очищення, parsing CSV, перетворення в `Experiment`, нормалізація;
- `filters.py` — streaming validation з лічильниками, фільтри за researcher, параметром, діапазоном;
- `analytics.py` — потокові середнє/мінімум/максимум, `pairwise`, `accumulate`, `groupby`;
- `pipeline.py` — lazy pipeline, `take` (islice), batching, пошук з early termination;
- `eager.py` — eager-версія для порівняння;
- `datagen.py` — генерація великих CSV із часткою некоректних записів.

Схема конвеєра:

```text
CSV -> read_data_lines() -> clean_lines() -> parse_rows() -> validate()
    -> filter_by_researcher() -> filter_by_parameter() -> filter_by_range()
    -> normalize() -> aggregate() / batched() / take()
```

## Запуск

```bash
python -m pip install -e .
experiment-registry iterators
experiment-registry stream data/experiments_sample.csv --parameter temperature --range 250 350
experiment-registry generate data/generated/experiments_100000.csv --count 100000
experiment-registry stream data/generated/experiments_100000.csv --researcher "Olena Kovalenko" --range 100 300
python benchmarks/benchmark_streaming.py
```

Згенеровані файли зберігаються в `data/generated/` і не додаються до Git.

## Автор

Накладюк Володимир, група ФеП-32
