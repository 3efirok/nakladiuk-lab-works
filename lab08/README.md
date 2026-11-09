# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №8 — мережеве та асинхронне програмування. REST API.

Варіант 15 — облік результатів наукових експериментів.

## REST API (`experiment_registry.api`)

| Method | Endpoint | Опис | Коди |
|--------|----------|------|------|
| GET | `/researchers` | список дослідників | 200 |
| POST | `/researchers` | додати дослідника | 201, 409, 422 |
| GET | `/researchers/{id}` | дослідник | 200, 404 |
| GET | `/researchers/{id}/experiments` | експерименти дослідника (`?sort=`) | 200, 404 |
| GET | `/experiments` | фільтри `researcher_id`, `parameter`, `min_result`, `max_result`, `sort`, `limit`, `offset` | 200, 422 |
| POST | `/experiments` | додати експеримент | 201, 404, 422 |
| GET | `/experiments/{id}` | експеримент | 200, 404 |
| PATCH | `/experiments/{id}` | часткова зміна (наприклад, результату) | 200, 404, 422 |
| DELETE | `/experiments/{id}` | видалення | 204, 404 |
| GET | `/experiments/statistics` | average / minimum / maximum (`?parameter=&researcher_id=`) | 200, 404 |
| GET | `/experiments/statistics/by-researcher?ids=1&ids=2` | паралельна статистика (Task, gather, Semaphore, timeout) | 200 |

Асинхронний клієнт `api/external.py` (`httpx.AsyncClient`): спільний пул з'єднань,
`asyncio.Semaphore`, timeout, retry з exponential backoff для мережевих помилок і 502–504.

## Запуск

```bash
python -m pip install -e ".[dev]"
alembic upgrade head
experiment-registry serve --port 8000          # або: uvicorn experiment_registry.api:app
# Swagger UI: http://127.0.0.1:8000/docs
experiment-registry api-client --base-url http://127.0.0.1:8000 --researchers 1 2 3
pytest -v
```

Приклад запиту:

```bash
curl -X POST http://127.0.0.1:8000/experiments -H "Content-Type: application/json" \
     -d '{"name": "Thermal conductivity of Al alloy", "researcher_id": 1,
          "parameter": "temperature", "result": 293.4, "date": "2026-02-03"}'
```

## Автор

Накладюк Володимир, група ФеП-32
