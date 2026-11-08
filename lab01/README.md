# Experiment Registry

Навчальний проєкт з дисципліни «Професійний Пайтон».
Лабораторна робота №1 — організація професійного Python-проєкту та Git.

Варіант 15 — облік результатів наукових експериментів.
Для кожного експерименту зберігаються назва, дослідник (researcher), параметр, результат і дата.

## Можливості

- додавання експерименту з перевіркою даних;
- пошук експериментів за дослідником;
- середнє значення, мінімум і максимум результатів;
- фільтрація результатів за заданим діапазоном;
- пошук за кількома критеріями та сортування;
- консольне меню з введенням даних із клавіатури.

## Вимоги

Python 3.11+

## Встановлення

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
```

## Запуск

Демонстраційний сценарій:

```bash
python -m experiment_registry.main
# або
experiment-registry
```

Інтерактивне меню:

```bash
python -m experiment_registry.main --menu
```

Приклад результату:

```text
Average temperature result: 267.38
Minimum: 77.20 -> #5 Cryogenic cooling run (Andrii Bondar)
Maximum: 348.90 -> #7 Heat exchanger efficiency (Olena Kovalenko)
```

## Структура проєкту

```text
lab01/
├── pyproject.toml
├── README.md
├── .gitignore
└── src/
    └── experiment_registry/
        ├── __init__.py      # версія пакета
        ├── config.py        # константи конфігурації
        ├── exceptions.py    # власні винятки
        ├── models.py        # data model Experiment
        ├── services.py      # бізнес-логіка
        └── main.py          # точка входу, демо та меню
```

## Автор

Накладюк Володимир, група ФеП-32
