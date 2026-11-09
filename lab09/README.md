# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №9 — паралельність, багатопроцесність та оптимізація.

Варіант 15 — облік результатів наукових експериментів.

## Що додано (`experiment_registry.performance`)

| Модуль | Вміст |
|--------|-------|
| `analytics.py` | baseline на Python-циклах і NumPy-версії: average, min, max, std, викиди, фільтр діапазону, статистика за дослідниками |
| `parallel.py` | map-reduce статистики через `ThreadPoolExecutor` / `ProcessPoolExecutor` (алгоритм Велфорда + злиття часткових моментів), паралельне завантаження файлів, `Lock` |
| `caching.py` | `CachedStatistics`: кеш для незмінного набору даних з інвалідацією за версією |
| `profiling.py` | `time_runs` (perf_counter), `profile_call` (cProfile), `peak_memory_mb` (tracemalloc) |

Production-оптимізація: `ExperimentRegistry.extended_statistics()` рахує статистику через NumPy і
кешує її до наступного запису; endpoint `GET /experiments/statistics/extended?parameter=...`.

## Експерименти

```bash
python -m pip install -e ".[dev]"
python benchmarks/benchmark_performance.py profile      # cProfile, пошук bottleneck
python benchmarks/benchmark_performance.py memory       # tracemalloc
python benchmarks/benchmark_performance.py benchmark    # 10k / 100k / 1M, 5 запусків, speedup
python benchmarks/benchmark_performance.py operations   # статистика за дослідниками, фільтр
python benchmarks/benchmark_performance.py workers      # 1, 2, 4, 8, 12 workers
python benchmarks/benchmark_performance.py cache io sync
pytest -v
```

Основний результат (1 000 000 значень): NumPy ≈ 40× швидше за Python-цикли, `ProcessPoolExecutor`
≈ 1.4–1.8× (обмежено передаванням даних між процесами), `ThreadPoolExecutor` не прискорює
CPU-bound задачу через GIL, але дає ≈ 5× для завантаження файлів з мережевою затримкою.

## Автор

Накладюк Володимир, група ФеП-32
