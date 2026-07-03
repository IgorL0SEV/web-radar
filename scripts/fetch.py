#!/usr/bin/env python
"""
web-radar fetch — сбор данных из внешних источников.

Команды:
  python scripts/fetch.py url <url> [--css <selector>]  — загрузить страницу, извлечь данные
  python scripts/fetch.py api <url> [--method GET|POST] [--data <json>]  — запрос к API
  python scripts/fetch.py file <path>  — загрузить данные из локального JSON-файла

Результат выводится в stdout как JSON — агент может использовать его напрямую.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

ROOT = Path(__file__).resolve().parents[1]


def fetch_url(url: str, selector: str = None, timeout: int = 30, user_agent: str = None):
    """Загрузить HTML-страницу и извлечь данные по CSS-селектору."""
    if not HAS_REQUESTS:
        return {"error": "Модуль requests не установлен. Установите: pip install requests"}
    if not HAS_BS4:
        return {"error": "Модуль beautifulsoup4 не установлен. Установите: pip install beautifulsoup4"}

    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Ошибка запроса: {e}"}

    if selector:
        soup = BeautifulSoup(response.text, "html.parser")
        elements = soup.select(selector)
        if not elements:
            return {"url": url, "selector": selector, "results": [], "count": 0}

        results = []
        for el in elements:
            results.append({
                "tag": el.name,
                "text": el.get_text(strip=True),
                "attrs": dict(el.attrs) if el.attrs else {},
            })
        return {"url": url, "selector": selector, "results": results, "count": len(results)}
    else:
        return {
            "url": url,
            "status_code": response.status_code,
            "content_length": len(response.text),
            "preview": response.text[:2000],
        }


def fetch_api(url: str, method: str = "GET", data: dict = None, timeout: int = 30, user_agent: str = None):
    """Выполнить запрос к REST API."""
    if not HAS_REQUESTS:
        return {"error": "Модуль requests не установлен. Установите: pip install requests"}

    headers = {"Content-Type": "application/json"}
    if user_agent:
        headers["User-Agent"] = user_agent

    try:
        if method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=timeout)
        else:
            response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"error": f"Ошибка API-запроса: {e}"}

    try:
        body = response.json()
    except json.JSONDecodeError:
        body = response.text[:2000]

    return {
        "url": url,
        "method": method.upper(),
        "status_code": response.status_code,
        "data": body,
    }


def fetch_file(path: str):
    """Загрузить данные из локального JSON-файла."""
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = ROOT / file_path

    if not file_path.exists():
        return {"error": f"Файл не найден: {file_path}"}

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"error": f"Ошибка чтения файла: {e}"}

    return {"source": str(file_path), "data": data}


def main():
    parser = argparse.ArgumentParser(description="web-radar fetch — сбор данных")
    sub = parser.add_subparsers(dest="command")

    p_url = sub.add_parser("url", help="Загрузить HTML-страницу")
    p_url.add_argument("url", help="URL страницы")
    p_url.add_argument("--css", help="CSS-селектор для извлечения данных")
    p_url.add_argument("--timeout", type=int, default=30)
    p_url.add_argument("--user-agent", default="WebRadar/1.0")

    p_api = sub.add_parser("api", help="Запрос к REST API")
    p_api.add_argument("url", help="URL API")
    p_api.add_argument("--method", default="GET", choices=["GET", "POST"])
    p_api.add_argument("--data", help="JSON-данные для POST")
    p_api.add_argument("--timeout", type=int, default=30)
    p_api.add_argument("--user-agent", default="WebRadar/1.0")

    p_file = sub.add_parser("file", help="Загрузить локальный JSON-файл")
    p_file.add_argument("path", help="Путь к файлу")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "url":
        result = fetch_url(args.url, selector=args.css, timeout=args.timeout, user_agent=args.user_agent)
    elif args.command == "api":
        data = json.loads(args.data) if args.data else None
        result = fetch_api(args.url, method=args.method, data=data, timeout=args.timeout, user_agent=args.user_agent)
    elif args.command == "file":
        result = fetch_file(args.path)
    else:
        result = {"error": f"Неизвестная команда: {args.command}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()