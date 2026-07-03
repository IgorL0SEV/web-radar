# Web Radar 📡

Агент мониторинга источников для OpenClaw. Проверяет настроенные источники, сравнивает с предыдущим состоянием и показывает только значимые изменения.

## Возможности

- **Мониторинг изменений** — отслеживает цены, наличие, новости и другие источники
- **Фильтрация шума** — пороги значимости (low/medium/high), дедупликация событий
- **Сбор данных из веба** — HTML-парсинг (CSS-селекторы), REST API, локальные файлы
- **Обработка документов** — .docx и .xlsx
- **Отчёты** — JSON-лог событий, Markdown-отчёты и сводки

## Структура

```
web-radar/
├── AGENTS.md              # Инструкции агента
├── SOUL.md                # Тон и стиль
├── IDENTITY.md            # Имя и назначение
├── USER.md                # Ожидания пользователя
├── TOOLS.md               # Справка по командам
├── HEARTBEAT.md           # Периодические проверки
├── config/
│   └── sources.json       # Конфигурация источников
├── data/
│   ├── demo-source.json   # Тестовые данные
│   └── state.json         # Текущее состояние (runtime)
├── logs/
│   └── events.jsonl       # Лог всех событий (runtime)
├── reports/
│   ├── latest-report.md   # Отчёт последней проверки (runtime)
│   └── daily-digest.md    # Сводка medium/high (runtime)
├── scripts/
│   ├── monitor.py          # Ядро: check, digest, status
│   ├── fetch.py            # Сбор данных: url, api, file
│   ├── parse_docs.py       # Обработка .docx и .xlsx
│   ├── change_demo_data.py # Управление демо-данными
│   └── reset_demo.py       # Сброс до начального состояния
├── requirements.txt
└── .gitignore
```

## Быстрый старт

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Демонстрация

```bash
# Сбросить данные до начального состояния
python scripts/reset_demo.py

# Первый запуск — создаёт baseline
python scripts/monitor.py check

# Имитировать изменение цены
python scripts/change_demo_data.py price-drop

# Проверить — обнаружит критическое изменение
python scripts/monitor.py check

# Повторная проверка — изменений нет
python scripts/monitor.py check

# Сводка medium/high событий
python scripts/monitor.py digest
```

### Сценарии демо-данных

| Сценарий | Описание |
|----------|----------|
| `price-drop` | Снижение цены на 20% (high) |
| `small-price-drop` | Незначительное снижение на 2% (low) |
| `out-of-stock` | Тариф недоступен (high) |
| `critical-news` | Новость с ключевыми словами (high) |
| `price-up` | Повышение цены на 10% (medium) |

## Команды

### monitor.py

```bash
python scripts/monitor.py check    # Проверить источники
python scripts/monitor.py digest    # Сформировать сводку
python scripts/monitor.py status    # Показать текущее состояние
```

### fetch.py

```bash
# HTML-страница с CSS-селектором (статический HTML)
python scripts/fetch.py url https://example.com --css ".price"

# SPA-сайт через Playwright (Wildberries, Ozon и т.п.)
python scripts/fetch.py browser "https://www.wildberries.by/catalog/672171989/detail.aspx" --css "[class*='price']" --wait 5

# REST API
python scripts/fetch.py api https://api.example.com/data

# Локальный JSON-файл
python scripts/fetch.py file data/demo-source.json
```

### parse_docs.py

```bash
# Извлечь текст из .docx
python scripts/parse_docs.py docx document.docx

# Извлечь таблицу из .xlsx
python scripts/parse_docs.py xlsx spreadsheet.xlsx --sheet 0 --max-rows 50
```

## Конфигурация источников

Источники настраиваются в `config/sources.json`. Поддерживаются три типа:

### number — числовое значение

```json
{
  "id": "competitor-business-price",
  "name": "Competitor A / тариф Business",
  "type": "number",
  "field": "competitor.business_price",
  "unit": "руб.",
  "medium_change_pct": 3,
  "high_change_pct": 7,
  "direction": "any",
  "action": "Проверить собственный тариф и рекламное предложение."
}
```

### boolean — статус доступности

```json
{
  "id": "competitor-business-availability",
  "name": "Competitor A / наличие тарифа",
  "type": "boolean",
  "field": "competitor.business_available",
  "high_when": false,
  "action": "Проверить причину снятия предложения."
}
```

### text — текстовые данные

```json
{
  "id": "market-news",
  "name": "Новости рынка",
  "type": "text",
  "field": "market.latest_news",
  "critical_keywords": ["повышение цен", "новый тариф", "закрытие", "санкции"],
  "action": "Оценить влияние новости."
}
```

## Уровни значимости

| Уровень | Описание |
|---------|----------|
| `low` | Незначительное изменение, фиксируется в логе |
| `medium` | Заслуживает упоминания в сводке |
| `high` | Критическое изменение, требует внимания |

## Запуск через OpenClaw

```bash
openclaw agent --agent web-radar --message "Проверь все источники и покажи только важные изменения."
```

## Лицензия

MIT