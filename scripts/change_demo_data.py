#!/usr/bin/env python
"""
web-radar change_demo_data — управляемое изменение тестовых данных.

Сценарии:
  python scripts/change_demo_data.py price-drop        — снижение цены на макадамию −20%
  python scripts/change_demo_data.py small-price-drop   — небольшое снижение цены −2%
  python scripts/change_demo_data.py out-of-stock        — товар недоступен
  python scripts/change_demo_data.py price-up            — повышение цены +10%
  python scripts/change_demo_data.py both-change         — оба товара меняются
  python scripts/change_demo_data.py both-out            — оба товара недоступны
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "demo-source.json"

# Базовые цены для демо
BASE_MACADAMIA = 29.08
BASE_PISTACHIO = 58.53


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else ""

    if not SOURCE_PATH.exists():
        print(json.dumps({"error": f"Файл {SOURCE_PATH} не найден. Запустите reset_demo.py сначала."}, ensure_ascii=False))
        sys.exit(1)

    data = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    wb = data["wildberries"]

    if scenario == "price-drop":
        # Макадамия: 29.08 → 23.26 BYN (−20%)
        wb["macadamia_672171989_price"] = 23.26
        msg = "📉 Макадамия: 29,08 → 23,26 BYN (−20%)"

    elif scenario == "small-price-drop":
        # Макадамия: 29.08 → 28.50 BYN (−2%)
        wb["macadamia_672171989_price"] = 28.50
        msg = "📉 Макадамия: 29,08 → 28,50 BYN (−2%)"

    elif scenario == "out-of-stock":
        wb["macadamia_672171989_available"] = False
        msg = "🚫 Макадамия: недоступен"

    elif scenario == "price-up":
        # Фисташки: 58.53 → 64,38 BYN (+10%)
        wb["pistachio_1164358226_price"] = 64.38
        msg = "📈 Фисташки: 58,53 → 64,38 BYN (+10%)"

    elif scenario == "both-change":
        # Макадамия −20%, фисташки +10%
        wb["macadamia_672171989_price"] = 23.26
        wb["pistachio_1164358226_price"] = 64.38
        msg = "📉 Макадамия −20%, 📈 Фисташки +10%"

    elif scenario == "both-out":
        wb["macadamia_672171989_available"] = False
        wb["pistachio_1164358226_available"] = False
        msg = "🚫 Оба товара недоступны"

    else:
        print(json.dumps({
            "error": "Неизвестный сценарий",
            "available": [
                "price-drop", "small-price-drop", "out-of-stock",
                "price-up", "both-change", "both-out",
            ],
        }, ensure_ascii=False))
        sys.exit(1)

    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    SOURCE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(msg)


if __name__ == "__main__":
    main()