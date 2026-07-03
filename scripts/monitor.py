#!/usr/bin/env python
"""
web-radar monitor — ядро мониторинга источников.

Команды:
  python scripts/monitor.py check   — проверить источники, сравнить с предыдущим состоянием
  python scripts/monitor.py digest  — сформировать сводку medium/high событий
  python scripts/monitor.py status  — показать текущее состояние

Windows-совместимо (python вместо python3, UTF-8 повсюду).
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
SOURCE_PATH = ROOT / "data" / "demo-source.json"
STATE_PATH = ROOT / "data" / "state.json"
EVENTS_PATH = ROOT / "logs" / "events.jsonl"
LATEST_REPORT_PATH = ROOT / "reports" / "latest-report.md"
DIGEST_PATH = ROOT / "reports" / "daily-digest.md"


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_field(data: dict, field: str):
    """Прочитать вложенное поле по dot-пути: 'competitor.business_price'."""
    current = data
    for part in field.split("."):
        current = current[part]
    return current


def make_event_id(source_id: str, old_value, new_value) -> str:
    raw = json.dumps([source_id, old_value, new_value], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def format_value(value, unit=None) -> str:
    if isinstance(value, bool):
        return "доступно" if value else "недоступно"
    if isinstance(value, (int, float)):
        rendered = f"{value:,.2f}".replace(",", " ")
        if rendered.endswith(".00"):
            rendered = rendered[:-3]
        return f"{rendered} {unit or ''}".strip()
    return str(value)


# ---------------------------------------------------------------------------
# Классификация изменений
# ---------------------------------------------------------------------------

def classify(source: dict, old_value, new_value):
    """Определить severity, процент изменения и причину."""
    source_type = source["type"]

    if source_type == "number":
        if old_value == 0:
            return "high", None, "Невозможно рассчитать процент от нулевой базы."
        change_pct = ((new_value - old_value) / old_value) * 100
        absolute_pct = abs(change_pct)
        if absolute_pct >= source["high_change_pct"]:
            severity = "high"
        elif absolute_pct >= source["medium_change_pct"]:
            severity = "medium"
        else:
            severity = "low"
        return severity, change_pct, "Изменилось числовое значение."

    if source_type == "boolean":
        severity = "high" if new_value == source.get("high_when") else "medium"
        return severity, None, "Изменился статус доступности."

    if source_type == "text":
        lowered = str(new_value).lower()
        matched = [
            kw for kw in source.get("critical_keywords", [])
            if kw.lower() in lowered
        ]
        if matched:
            return "high", None, f"Найдены ключевые слова: {', '.join(matched)}."
        return "medium", None, "Появился новый текст."

    return "low", None, "Значение изменилось."


# ---------------------------------------------------------------------------
# Логирование событий
# ---------------------------------------------------------------------------

def append_event(event: dict):
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def load_events() -> list:
    if not EVENTS_PATH.exists():
        return []
    events = []
    for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# Отчёты
# ---------------------------------------------------------------------------

def make_report(status: str, checked_count: int, events: list, duplicates: int):
    lines = [
        "# Отчёт мониторинга",
        "",
        f"- Статус: `{status}`",
        f"- Проверено источников: {checked_count}",
        f"- Новых событий: {len(events)}",
        f"- Повторных событий пропущено: {duplicates}",
        "",
    ]
    if not events:
        lines.extend(["## Результат", "", "Значимых новых изменений нет.", ""])
    else:
        lines.extend(["## Новые события", ""])
        for event in events:
            lines.extend([
                f"### {event['name']}",
                "",
                f"- Уровень: **{event['severity']}**",
                f"- Было: {event['old_display']}",
                f"- Стало: {event['new_display']}",
            ])
            if event.get("change_pct") is not None:
                lines.append(f"- Изменение: {event['change_pct']:+.1f}%")
            lines.extend([
                f"- Почему важно: {event['reason']}",
                f"- Рекомендуемое действие: {event['action']}",
                f"- ID события: `{event['event_id']}`",
                "",
            ])

    LATEST_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    LATEST_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def make_digest(events: list, digested_ids: set) -> tuple:
    """Формирует сводку medium/high событий. Возвращает (текст_сводки, новые_digested_ids)."""
    filtered = [
        e for e in events
        if e.get("severity") in {"medium", "high"}
        and e.get("event_id") not in digested_ids
    ]
    lines = [
        "# Ежедневная сводка мониторинга",
        "",
        f"Событий среднего и высокого уровня: {len(filtered)}.",
        "",
    ]
    if not filtered:
        lines.append("Значимых событий пока нет.")
    else:
        for event in filtered[-20:]:
            lines.extend([
                f"## {event['name']}",
                "",
                f"- Уровень: **{event['severity']}**",
                f"- Было: {event['old_display']}",
                f"- Стало: {event['new_display']}",
                f"- Действие: {event['action']}",
                "",
            ])
    new_ids = digested_ids | {e["event_id"] for e in filtered}
    return "\n".join(lines), new_ids


# ---------------------------------------------------------------------------
# Команды
# ---------------------------------------------------------------------------

def check():
    """Проверить источники, сравнить с предыдущим состоянием."""
    config = load_json(CONFIG_PATH)
    current = load_json(SOURCE_PATH)
    state = load_json(STATE_PATH)

    current_values = {
        source["id"]: read_field(current, source["field"])
        for source in config["sources"]
    }

    # Первый запуск — сохраняем baseline
    if not state.get("initialized"):
        state = {
            "initialized": True,
            "last_checked_at": datetime.now(timezone.utc).isoformat(),
            "values": current_values,
            "sent_event_ids": [],
            "digested_event_ids": [],
        }
        save_json(STATE_PATH, state)
        make_report("baseline_created", len(config["sources"]), [], 0)
        print(json.dumps({
            "status": "baseline_created",
            "checked_sources": len(config["sources"]),
            "new_events": [],
            "message": "Базовое состояние сохранено.",
            "report": str(LATEST_REPORT_PATH),
        }, ensure_ascii=False, indent=2))
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    sent_ids = set(state.get("sent_event_ids", []))
    new_events = []
    low_events_logged = 0
    duplicates = 0

    for source in config["sources"]:
        source_id = source["id"]
        old_value = state.get("values", {}).get(source_id)
        new_value = current_values[source_id]

        if old_value == new_value:
            continue

        severity, change_pct, reason = classify(source, old_value, new_value)
        event_id = make_event_id(source_id, old_value, new_value)

        event = {
            "event_id": event_id,
            "created_at": timestamp,
            "source_id": source_id,
            "name": source["name"],
            "severity": severity,
            "old_value": old_value,
            "new_value": new_value,
            "old_display": format_value(old_value, source.get("unit")),
            "new_display": format_value(new_value, source.get("unit")),
            "change_pct": change_pct,
            "reason": reason,
            "action": source["action"],
        }
        append_event(event)

        if severity == "low":
            low_events_logged += 1
        elif event_id in sent_ids:
            duplicates += 1
        else:
            new_events.append(event)
            sent_ids.add(event_id)

    state["last_checked_at"] = timestamp
    state["values"] = current_values
    state["sent_event_ids"] = sorted(sent_ids)
    save_json(STATE_PATH, state)

    status = "changes_detected" if new_events else "no_changes"
    make_report(status, len(config["sources"]), new_events, duplicates)

    print(json.dumps({
        "status": status,
        "checked_sources": len(config["sources"]),
        "new_events": new_events,
        "low_events_logged": low_events_logged,
        "duplicates_skipped": duplicates,
        "report": str(LATEST_REPORT_PATH),
    }, ensure_ascii=False, indent=2))


def digest():
    """Сформировать сводку medium/high событий."""
    state = load_json(STATE_PATH)
    digested_ids = set(state.get("digested_event_ids", []))
    events = load_events()

    text, new_ids = make_digest(events, digested_ids)
    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_PATH.write_text(text, encoding="utf-8")

    state["digested_event_ids"] = sorted(new_ids)
    state["last_digest_at"] = datetime.now(timezone.utc).isoformat()
    save_json(STATE_PATH, state)

    print(json.dumps({
        "status": "digest",
        "event_count": len([
            e for e in events
            if e.get("severity") in {"medium", "high"}
            and e.get("event_id") not in digested_ids
        ]),
        "report": str(DIGEST_PATH),
    }, ensure_ascii=False, indent=2))


def status():
    """Показать текущее состояние мониторинга."""
    state = load_json(STATE_PATH)
    print(json.dumps({
        "initialized": state.get("initialized", False),
        "last_checked_at": state.get("last_checked_at"),
        "values": state.get("values", {}),
        "sent_events": len(state.get("sent_event_ids", [])),
        "digested_events": len(state.get("digested_event_ids", [])),
        "event_log_entries": len(load_events()),
    }, ensure_ascii=False, indent=2))


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    if command == "check":
        check()
    elif command == "digest":
        digest()
    elif command == "status":
        status()
    else:
        raise SystemExit("Использование: monitor.py [check|digest|status]")


if __name__ == "__main__":
    main()