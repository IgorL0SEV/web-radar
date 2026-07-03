#!/usr/bin/env python
"""
web-radar reset_demo — сброс всех данных до начального состояния.
"""

import json
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]

SOURCE = {
    "wildberries": {
        "macadamia_672171989_price": 0,
        "macadamia_672171989_available": True,
    },
    "updated_at": "2026-07-01T09:00:00+03:00",
}

STATE = {
    "initialized": False,
    "values": {},
    "sent_event_ids": [],
    "digested_event_ids": [],
}


def main():
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(parents=True, exist_ok=True)
    (ROOT / "reports").mkdir(parents=True, exist_ok=True)

    (ROOT / "data" / "demo-source.json").write_text(
        json.dumps(SOURCE, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "data" / "state.json").write_text(
        json.dumps(STATE, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (ROOT / "logs" / "events.jsonl").write_text("", encoding="utf-8")
    (ROOT / "reports" / "latest-report.md").write_text(
        "# Мониторинг сброшен\n", encoding="utf-8",
    )
    (ROOT / "reports" / "daily-digest.md").write_text(
        "# Сводка пока не сформирована\n", encoding="utf-8",
    )

    print("Демонстрация сброшена. Запустите fetch-and-update для загрузки реальных данных.")


if __name__ == "__main__":
    main()