#!/usr/bin/env python
"""
web-radar fetch — сбор данных из внешних источников.

Команды:
  python scripts/fetch.py url <url> [--css <selector>]  — загрузить страницу, извлечь данные
  python scripts/fetch.py browser <url> [--css <selector>] [--wait <seconds>]  — загрузить через Playwright (SPA)
  python scripts/fetch.py api <url> [--method GET|POST] [--data <json>]  — запрос к API
  python scripts/fetch.py file <path>  — загрузить данные из локального JSON-файла

Результат выводится в stdout как JSON — агент может использовать его напрямую.
"""

import argparse
import json
import sys
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

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

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

ROOT = Path(__file__).resolve().parents[1]


def fetch_url(url: str, selector: str = None, timeout: int = 30, user_agent: str = None):
    """Загрузить HTML-страницу и извлечь данные по CSS-селектору (статический HTML)."""
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


def fetch_browser(url: str, selector: str = None, wait: float = 3, user_agent: str = None, extract_links: bool = False):
    """Загрузить страницу через Playwright (headless Chromium) — для SPA-сайтов.

    Поддерживает:
    - CSS-селектор для извлечения элементов
    - Ожидание рендера JavaScript (wait секунды)
    - Извлечение ссылок (extract_links)
    - Если селектор не указан — возвращает заголовок и текст страницы
    """
    if not HAS_PLAYWRIGHT:
        return {"error": "Модуль playwright не установлен. Установите: pip install playwright && python -m playwright install chromium"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            browser.close()
            return {"error": f"Ошибка загрузки страницы: {e}"}

        # Ждём рендер JS
        page.wait_for_timeout(int(wait * 1000))

        result = {"url": url, "mode": "browser"}

        if selector:
            elements = page.query_selector_all(selector)
            if not elements:
                result["selector"] = selector
                result["results"] = []
                result["count"] = 0
                browser.close()
                return result

            results = []
            for el in elements:
                text = el.inner_text()
                tag = el.evaluate("el => el.tagName.toLowerCase()")
                attrs = el.evaluate("el => { try { return Object.fromEntries(Array.from(el.attributes).map(a => [a.name, a.value])); } catch(e) { return {}; }}")
                entry = {
                    "tag": tag,
                    "text": text.strip(),
                    "attrs": attrs,
                }
                if extract_links:
                    href = el.evaluate("el => el.href || el.closest('a')?.href || null")
                    if href:
                        entry["href"] = href
                results.append(entry)

            result["selector"] = selector
            result["results"] = results
            result["count"] = len(results)
        else:
            # Без селектора — заголовок и основной текст
            title = page.title()
            body_text = page.query_selector("body").inner_text() if page.query_selector("body") else ""
            # Ограничиваем текст 5000 символов
            result["title"] = title
            result["text_length"] = len(body_text)
            result["text_preview"] = body_text[:5000]

            # Пытаемся найти цену по распространённым селекторам
            price_selectors = [
                "[class*='price'] [class*='lower']",
                "[class*='price'] [class*='sale']",
                "[class*='price-block']",
                "[class*='product-price']",
                ".price",
            ]
            for ps in price_selectors:
                els = page.query_selector_all(ps)
                if els:
                    prices = [el.inner_text().strip() for el in els[:5]]
                    result["auto_price_candidates"] = prices
                    break

        browser.close()
        return result


def fetch_api(url: str, method: str = "GET", data: dict = None, timeout: int = 30, user_agent: str = None):
    """Выполнить запрос к REST API."""
    if not HAS_REQUESTS:
        return {"error": "Модуль requests не установлен. Установите: pip install requests"}

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
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

    p_url = sub.add_parser("url", help="Загрузить HTML-страницу (статический HTML)")
    p_url.add_argument("url", help="URL страницы")
    p_url.add_argument("--css", help="CSS-селектор для извлечения данных")
    p_url.add_argument("--timeout", type=int, default=30)
    p_url.add_argument("--user-agent", default="WebRadar/1.0")

    p_browser = sub.add_parser("browser", help="Загрузить страницу через Playwright (SPA, JS-рендеринг)")
    p_browser.add_argument("url", help="URL страницы")
    p_browser.add_argument("--css", help="CSS-селектор для извлечения данных")
    p_browser.add_argument("--wait", type=float, default=3, help="Ожидание рендера JS (секунды, по умолчанию 3)")
    p_browser.add_argument("--extract-links", action="store_true", help="Извлечь ссылки из элементов")
    p_browser.add_argument("--user-agent", default=None, help="User-Agent (по умолчанию Chrome)")

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
    elif args.command == "browser":
        result = fetch_browser(
            args.url,
            selector=args.css,
            wait=args.wait,
            user_agent=args.user_agent,
            extract_links=args.extract_links,
        )
    elif args.command == "browser":
        result = fetch_browser(
            args.url,
            selector=args.css,
            wait=args.wait,
            user_agent=args.user_agent,
            extract_links=args.extract_links,
        )
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