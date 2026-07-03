#!/usr/bin/env python
"""
web-radar change_demo_data — управляемое изменение тестовых данных.

Сценарии:
  python scripts/change_demo_data.py price-drop       — снижение цены на 20%
  python scripts/change_demo_data.py small-price-drop  — небольшое снижение цены
  python scripts/change_demo_data.py out-of-stock       — товар недоступен
  python scripts/change_demo_data.py critical-news      — критическая новость
  python scripts/change_demo_data.py price-up           — повышение цены
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "demo-source.json"


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else ""

    if not SOURCE_PATH.exists():
        print(json.dumps({"error": f"Файл {SOURCE_PATH} не найден. Запустите reset_demo.py сначала."}, ensure_ascii=False))
        sys.exit(1)

    data = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    if scenario == "price-drop":
        data["competitor"]["business_price"] = 3990
        message = "Цена изменена: 4 990 → 3 990 руб. (−20%)"
    elif scenario == "small-price-drop":
        data["competitor"]["business_price"] = 4890
        message = "Цена изменена: 4 990 → 4 890 руб. (−2%)"
    elif scenario == "out-of-stock":
        data["competitor"]["business_available"] = False
        message = "Тариф помечен как недоступный."
    elif scenario == "critical-news":
        data["market"]["latest_news"] = (
            "Конкурент объявил новый тариф и повышение цен с 1 июля."
        )
        message = "Добавлена критическая новость."
    elif scenario == "price-up":
        data["competitor"]["business_price"] = 5490
        message = "Цена изменена: 4 990 → 5 490 руб. (+10%)"
    else:
        print(json.dumps({
            "error": "Неизвестный сценарий",
            "available": ["price-drop", "small-price-drop", "out-of-stock", "critical-news", "price-up"],
        }, ensure_ascii=False))
        sys.exit(1)

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    SOURCE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(message)


if __name__ == "__main__":
    main()