# Experiment Registry

Production-версія навчального проєкту з дисципліни «Професійний Пайтон» (лабораторна робота №10).
Варіант 15 — облік результатів наукових експериментів: назва експерименту, дослідник, параметр,
результат і дата.

Пакет: `experiment-registry` (модуль `experiment_registry`), версія 1.0.0.

## Можливості

- додавання дослідників та експериментів, пошук за дослідником, average / minimum / maximum,
  фільтрація за діапазоном, сортування за датою;
- REST API на FastAPI з Pydantic-валідацією та Swagger UI (`/docs`);
- persistence layer: SQLite + SQLAlchemy 2.0, міграції Alembic;
- імпорт CSV / експорт JSON з YAML-конфігурацією, потокова обробка великих файлів;
- оптимізована статистика (NumPy + кеш з інвалідацією), паралельні запити через HTTPX;
- `GET /health` для Docker HEALTHCHECK.

## Встановлення (локально)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env            # за потреби змінити значення
alembic upgrade head
experiment-registry serve       # http://127.0.0.1:8000/docs
```

## Конфігурація

Усі налаштування читаються зі змінних середовища (або з `.env`, який не потрапляє в Git):

| Змінна | За замовчуванням | Опис |
|--------|------------------|------|
| `DATABASE_URL` | `sqlite:///experiments.db` | URL бази даних SQLAlchemy |
| `ENVIRONMENT` (`APP_ENV`) | `development` | `development`, `test`, `production` |
| `LOG_LEVEL` | `INFO` | рівень журналювання |
| `API_TOKEN` | не задано | якщо задано, POST/PATCH/DELETE потребують заголовка `X-API-Token` |

Справжні паролі, токени й ключі не зберігаються в коді, README, Dockerfile чи Git; приклад
змінних — у `.env.example`.

## API

| Method | Endpoint | Опис |
|--------|----------|------|
| GET | `/health` | стан застосунку та бази |
| GET, POST | `/researchers` | список / додавання дослідників |
| GET | `/researchers/{id}`, `/researchers/{id}/experiments` | дослідник і його експерименти |
| GET, POST | `/experiments` | список (фільтри `researcher_id`, `parameter`, `min_result`, `max_result`, `sort`, `limit`, `offset`) / додавання |
| GET, PATCH, DELETE | `/experiments/{id}` | експеримент: читання, зміна, видалення |
| GET | `/experiments/statistics` | average, minimum, maximum (SQL) |
| GET | `/experiments/statistics/extended` | mean, std, median, p95 (NumPy, кеш) |
| GET | `/experiments/statistics/by-researcher?ids=1&ids=2` | паралельна статистика кількох дослідників |

## Docker

```bash
docker build -t experiment-registry:1.0.0 .
docker run -d --name experiment-registry -p 8000:8000 \
    -v experiment-data:/data -e LOG_LEVEL=INFO experiment-registry:1.0.0
curl http://127.0.0.1:8000/health
```

Образ багатоетапний (wheel збирається в окремому stage), працює від непривілейованого користувача,
при старті застосовує міграції, база зберігається в томі `/data`.

## Тести та якість коду

```bash
ruff check .
ruff format --check .
mypy
pytest -v --cov
python -m build                 # dist/*.whl та dist/*.tar.gz
```

## CI/CD

GitHub Actions (`.github/workflows/lab10-ci.yml` у корені репозиторію, бо GitHub читає workflows
лише звідти) для кожного push у `lab10/` виконує: ruff check, ruff format --check, mypy,
pytest з coverage на Python 3.12 і 3.13, збирання wheel/sdist з перевіркою встановлення, docker build
та перевірку `/health` у запущеному контейнері.

## Сценарій демонстрації

1. `pytest -v`, `ruff check .`, `mypy` — перевірка якості.
2. `python -m build` — wheel і sdist у `dist/`.
3. `docker build ...`, `docker run ...` — запуск контейнера з томом.
4. `curl /health`, Swagger UI `/docs`: додати дослідника, експеримент, змінити результат,
   отримати статистику.
5. Сторінка GitHub Actions — зелений pipeline.

## Автор

Накладюк Володимир, група ФеП-32. Ліцензія MIT.
