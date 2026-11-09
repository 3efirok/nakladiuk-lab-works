# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №7 — робота з базами даних у Python.

Варіант 15 — облік результатів наукових експериментів (назва, дослідник, параметр, результат, дата).

## Persistence layer (`experiment_registry.persistence`)

| Модуль | Вміст |
|--------|-------|
| `database.py` | engine, `sessionmaker`, `Base`, `PRAGMA foreign_keys = ON`, unit of work `session_scope` (commit/rollback) |
| `orm.py` | `ResearcherORM` (`researchers`) і `ExperimentORM` (`experiments`), зв'язок one-to-many |
| `repositories.py` | `ResearcherRepository`, `ExperimentRepository`: CRUD, пошук, діапазон, AVG/MIN/MAX, GROUP BY, пагінація |
| `services.py` | `ExperimentRegistry`: транзакційне додавання серії експериментів з rollback |
| `dbapi.py` | sqlite3 (DB-API) з параметризованими запитами |

Схема БД:

```text
researchers (id PK, full_name UNIQUE, email UNIQUE, department)
     1
     │
     * experiments (id PK, name, researcher_id FK -> researchers.id ON DELETE CASCADE,
                    parameter, result, date, notes)
```

## Міграції (Alembic)

```bash
alembic upgrade head        # 0001 create researchers and experiments, 0002 add experiment notes
alembic current
alembic history
alembic downgrade -1
```

URL бази задається в `alembic.ini` або змінною середовища `DATABASE_URL`.

## Запуск

```bash
python -m pip install -e ".[dev]"
alembic upgrade head
experiment-registry db                       # CRUD, агрегати, транзакція з rollback, DB-API
pytest -v                                    # integration tests використовують окрему БД у tmp_path
```

## Автор

Накладюк Володимир, група ФеП-32
