# TOOLS.md

## Навык

```text
~/.openclaw/skills/web-radar/SKILL.md
```

## Проверка источников

```bash
python scripts/monitor.py check
```

## Ежедневная сводка

```bash
python scripts/monitor.py digest
```

## Текущее состояние

```bash
python scripts/monitor.py status
```

## Сбор данных из внешних источников

```bash
# Статический HTML
python scripts/fetch.py url <url> [--css <selector>]

# SPA-сайты (Wildberries, Ozon и т.п.)
python scripts/fetch.py browser <url> [--css <selector>] [--wait <seconds>]

# REST API
python scripts/fetch.py api <url> [--method GET|POST] [--data <json>]

# Локальный файл
python scripts/fetch.py file <path>
```

## Обработка документов

```bash
python scripts/parse_docs.py docx <path>
python scripts/parse_docs.py xlsx <path> [--sheet <name>] [--max-rows <N>]
```

## Управляемая демонстрация

```bash
python scripts/reset_demo.py
python scripts/change_demo_data.py price-drop
python scripts/change_demo_data.py small-price-drop
python scripts/change_demo_data.py out-of-stock
python scripts/change_demo_data.py critical-news
python scripts/change_demo_data.py price-up
```