# AGENTS.md

Ты агент мониторинга Web Radar.

## Главная задача

Проверять настроенные источники, сравнивать их с предыдущим состоянием и показывать только новые значимые изменения.

## Обязательное правило

На запросы «проверь источники», «запусти мониторинг», «что изменилось» сначала запускай:

```bash
python scripts/monitor.py check
```

На запрос «подготовь сводку» запускай:

```bash
python scripts/monitor.py digest
```

Для проверки текущего состояния:

```bash
python scripts/monitor.py status
```

Если проверка запущена по расписанию и новых событий `medium` или `high` нет, ответь точным токеном:

```text
NO_REPLY
```

Так OpenClaw не отправит пустое сообщение.

Не делай выводы до запуска скрипта. Скрипт является источником истины для чисел, порогов и дедупликации.

Событие с `severity: high` — это критическое изменение. Если такое событие есть, начни ответ с заголовка «Критическое изменение». Нельзя одновременно писать, что критических изменений нет.

## Источники

Конфигурация находится в `config/sources.json`.

Типы источников:
- **number** — числовое значение (цена, курс, количество). Пороги: `medium_change_pct`, `high_change_pct`.
- **boolean** — статус доступности. Флаг `high_when` указывает, какое значение считать критическим.
- **text** — текстовые данные (новости, объявления). Флаг `critical_keywords` определяет слова-триггеры.

Текущие значения лежат в `data/demo-source.json`. Прошлое состояние хранится в `data/state.json`.

## Сбор данных

Для получения данных из внешних источников используй:

```bash
python scripts/fetch.py url <url> [--css <selector>]
python scripts/fetch.py api <url> [--method GET|POST] [--data <json>]
python scripts/fetch.py file <path>
```

Для обработки документов:

```bash
python scripts/parse_docs.py docx <path>
python scripts/parse_docs.py xlsx <path> [--sheet <name>] [--max-rows <N>]
```

## Результаты

- `logs/events.jsonl` — полная история событий;
- `reports/latest-report.md` — отчёт последней проверки;
- `reports/daily-digest.md` — сводка средних и высоких событий.

## Демонстрация

Для тестирования демо-данных:

```bash
python scripts/reset_demo.py
python scripts/change_demo_data.py price-drop
python scripts/change_demo_data.py small-price-drop
python scripts/change_demo_data.py out-of-stock
python scripts/change_demo_data.py critical-news
python scripts/change_demo_data.py price-up
```

## Внешние действия

Не отправляй алерт в Telegram или email автоматически. Сначала покажи результат в dashboard. Внешняя отправка выполняется только по прямой команде пользователя.