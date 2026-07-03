#!/usr/bin/env python3
"""
web-radar monitor — fetch prices from Wildberries.by and Onliner.by
Usage: python scripts/monitor.py fetch-and-update

Rules documented in SOURCE_CONFIGS.md:
- WB: Playwright ONLY (API blocked for non-browser, SPA renders via JS)
- WB: Sale prices from PAGE (not API — API gives ~11% lower for BY region)
- WB: API reliable for: name, brand, rating, feedbacks, basic price, stock
- Onliner: Open REST API, no Playwright needed
- Onliner: Shop name field is `title`, NOT `name`
- Onliner: Show top-3 offers with shop names, prices, delivery, links
"""
import json
import os
import sys
import re
import time
import yaml
import requests
from datetime import datetime, timezone, timedelta

# Fix encoding for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

# Timezone for Belarus
BY_TZ = timezone(timedelta(hours=3))

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PRICES_FILE = os.path.join(DATA_DIR, "prices.json")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.yaml")


def load_products():
    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prices():
    if os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"wb": {}, "onliner": {}, "last_check": None}


def save_prices(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── Wildberries.by ───────────────────────────────────────────────
# See SOURCE_CONFIGS.md for detailed notes on why Playwright is required
# and why API prices are unreliable for BY region sale prices.
def fetch_wb_product(nm_id):
    """Fetch product from WB.by using Playwright.
    
    Price strategy (per SOURCE_CONFIGS.md):
    - Sale price: from rendered PAGE (trustworthy, what user sees)
    - Basic price: from API (matches page, reliable)
    - API sale price (product field): ~11% lower than page, DO NOT USE for user reports
    - Name, brand, rating, stock: from API (reliable)
    """
    from playwright.sync_api import sync_playwright
    
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="ru-RU",
        )
        page = context.new_page()
        
        api_data = {}
        def handle_response(response):
            if "/__internal/u-card/cards/v4/detail" in response.url:
                try:
                    if response.status == 200:
                        body = json.loads(response.text())
                        for prod in body.get("products", []):
                            if prod.get("id") == nm_id:
                                api_data.update(prod)
                except:
                    pass
        
        page.on("response", handle_response)
        
        url = f"https://www.wildberries.by/catalog/{nm_id}/detail.aspx"
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)
        except Exception as e:
            result["error"] = f"Navigation: {str(e)[:150]}"
        
        # Extract VISIBLE prices from page (trustworthy source for sale price)
        try:
            page_info = page.evaluate("""() => {
                const result = { prices: [] };
                const els = document.querySelectorAll('[class*="price"]');
                const seen = new Set();
                els.forEach(el => {
                    const t = el.innerText.trim().replace(/\\s+/g, ' ');
                    if (t && /\\d/.test(t) && !seen.has(t)) {
                        seen.add(t);
                        result.prices.push(t);
                    }
                });
                return result;
            }""")
            result["page_prices"] = page_info.get("prices", [])
        except Exception as e:
            result["page_prices"] = []
        
        # Extract data from intercepted API response
        if api_data:
            result["name"] = api_data.get("name", "")
            result["brand"] = api_data.get("brand", "")
            result["rating"] = api_data.get("reviewRating", 0)
            result["feedbacks"] = api_data.get("feedbacks", 0)
            result["totalQuantity"] = api_data.get("totalQuantity", 0)
            
            sizes = api_data.get("sizes", [])
            if sizes:
                price = sizes[0].get("price", {})
                result["basic_price"] = price.get("basic", 0) / 100  # reliable
                # Note: api_product price is NOT used — it's ~11% lower than page
                # See SOURCE_CONFIGS.md for details
        
        # Parse visible prices: "29,08 ƃ 61,77 ƃ" → sale=29.08, basic=61.77
        if result.get("page_prices"):
            first_price_str = result["page_prices"][0]
            nums = re.findall(r'([\d\s]+,\d{2})', first_price_str.replace('\xa0', ' '))
            if len(nums) >= 2:
                result["sale_price"] = float(nums[0].replace('\xa0', '').replace(' ', '').replace(',', '.'))
                result["basic_price_page"] = float(nums[1].replace('\xa0', '').replace(' ', '').replace(',', '.'))
            elif len(nums) == 1:
                result["sale_price"] = float(nums[0].replace('\xa0', '').replace(' ', '').replace(',', '.'))
        
        browser.close()
    
    return result


# ─── Onliner.by ───────────────────────────────────────────────────
# See SOURCE_CONFIGS.md for API endpoints and field names.
# Key rules:
# - Shop name field: `title`, NOT `name`
# - Open REST API, no Playwright needed
# - Top-3 offers with shop names, prices, delivery, links
def fetch_onliner_product(product_key):
    """Fetch product from Onliner.by via open REST API."""
    result = {}
    
    # Product info
    try:
        r = requests.get(f"https://catalog.api.onliner.by/products/{product_key}", timeout=15)
        if r.status_code == 200:
            data = r.json()
            result["name"] = data.get("full_name", "")
            result["rating"] = data.get("reviews", {}).get("rating", 0)
            result["review_count"] = data.get("reviews", {}).get("count", 0)
            result["product_html_url"] = data.get("html_url", "")  # Direct product URL
            
            prices = data.get("prices", {})
            result["min_price"] = float(prices.get("price_min", {}).get("amount", 0))
            result["max_price"] = float(prices.get("price_max", {}).get("amount", 0))
            result["offers_count"] = prices.get("offers", {}).get("count", 0)
            
            sale = data.get("sale", {})
            result["on_sale"] = sale.get("is_on_sale", False)
            result["discount"] = sale.get("discount", 0)
    except Exception as e:
        result["error"] = str(e)[:150]
    
    # Offers / positions — top 3 with shop names
    try:
        r = requests.get(f"https://shop.api.onliner.by/products/{product_key}/positions", timeout=15)
        if r.status_code == 200:
            data = r.json()
            offers = data.get("positions", {}).get("primary", [])
            offers.sort(key=lambda x: float(x["position_price"]["amount"]))
            
            top3 = []
            for offer in offers[:3]:
                shop_id = offer["shop_id"]
                price = float(offer["position_price"]["amount"])
                
                # Get shop info — use `title` field, NOT `name`!
                try:
                    sr = requests.get(f"https://shop.api.onliner.by/shops/{shop_id}?include=full", timeout=10)
                    if sr.status_code == 200:
                        sd = sr.json()
                        shop_name = sd.get("title") or sd.get("name", f"Магазин #{shop_id}")
                    else:
                        shop_name = f"Магазин #{shop_id}"
                except:
                    shop_name = f"Магазин #{shop_id}"
                
                cobrand = offer.get("cobrand_info") or {}
                cashback = float(cobrand.get("cashback", {}).get("amount", 0)) if cobrand.get("cashback") else 0
                cashback_pct = cobrand.get("cashback_percentage", 0) if cobrand.get("cashback") else 0
                
                pickup = (offer.get("delivery") or {}).get("pickup_point")
                delivery = pickup.get("price_text", "") if pickup else ""
                
                top3.append({
                    "shop": shop_name,
                    "price": price,
                    "shop_url": f"https://{shop_id}.shop.onliner.by",
                    "cashback": cashback,
                    "cashback_pct": cashback_pct,
                    "delivery": delivery,
                    "on_sale": offer.get("on_sale", False),
                })
            
            result["top3"] = top3
    except Exception as e:
        result["offers_error"] = str(e)[:150]
    
    return result


# ─── Main ─────────────────────────────────────────────────────────
def fetch_and_update():
    products = load_products()
    data = load_prices()
    old_data = json.loads(json.dumps(data))  # deep copy for comparison
    
    now = datetime.now(BY_TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
    changes = []
    
    # ── WB products ──
    wb_products = products.get("wb", [])
    
    print("=" * 60)
    print("Wildberries.by")
    print("=" * 60)
    
    for prod in wb_products:
        nm_id = prod["nmId"]
        default_name = prod.get("name", "")
        url = prod.get("url", f"https://www.wildberries.by/catalog/{nm_id}/detail.aspx")
        
        print(f"\nЗапрос WB {nm_id}: {default_name}...")
        result = fetch_wb_product(nm_id)
        
        if result.get("error"):
            print(f"  ОШИБКА: {result['error']}")
            changes.append(f"WB {nm_id}: ОШИБКА — {result['error']}")
            continue
        
        name = result.get("name") or default_name
        sale = result.get("sale_price")
        basic = result.get("basic_price")
        
        old = old_data.get("wb", {}).get(str(nm_id), {})
        old_sale = old.get("last_price")
        
        comment_parts = []
        if sale is not None:
            if old_sale is not None:
                diff = round(sale - old_sale, 2)
                if diff > 0:
                    comment_parts.append(f"⬆ +{diff} BYN")
                elif diff < 0:
                    comment_parts.append(f"⬇ {diff} BYN")
                else:
                    comment_parts.append("без изменений")
            else:
                comment_parts.append("первая проверка")
        
        comment = ", ".join(comment_parts) if comment_parts else "нет данных о цене"
        
        print(f"  {name}")
        print(f"  Ссылка: {url}")
        print(f"  Цена: {sale} BYN (базовая: {basic} BYN) — {comment}")
        if result.get("rating"):
            print(f"  Рейтинг: {result['rating']} ★ | {result.get('feedbacks', '?')} отзывов")
        if result.get("totalQuantity") is not None:
            print(f"  В наличии: {'да' if result['totalQuantity'] > 0 else 'нет'} ({result['totalQuantity']} шт)")
        
        if "wb" not in data:
            data["wb"] = {}
        data["wb"][str(nm_id)] = {
            "name": name,
            "last_price": sale,
            "last_basic": basic,
            "url": url,
            "rating": result.get("rating"),
            "feedbacks": result.get("feedbacks"),
        }
        
        changes.append(f"WB {nm_id}: {sale} BYN ({comment})")
    
    # ── Onliner products ──
    onliner_products = products.get("onliner", [])
    
    print(f"\n{'=' * 60}")
    print("Onliner.by")
    print("=" * 60)
    
    for prod in onliner_products:
        key = prod["key"]
        default_name = prod.get("name", "")
        url = prod.get("url", "")
        prices_url = prod.get("prices_url", "")
        
        print(f"\nЗапрос Onliner {key}: {default_name}...")
        result = fetch_onliner_product(key)
        
        if result.get("error"):
            print(f"  ОШИБКА: {result['error']}")
            changes.append(f"Onliner {key}: ОШИБКА — {result['error']}")
            continue
        
        name = result.get("name") or default_name
        min_p = result.get("min_price")
        max_p = result.get("max_price")
        
        # Use URL from API if available, fall back to config
        product_url = result.get("product_html_url") or url
        if product_url and not prices_url:
            prices_url = f"{product_url}/prices"
        
        old = old_data.get("onliner", {}).get(key, {})
        old_min = old.get("last_min_price")
        
        comment_parts = []
        if min_p is not None:
            if old_min is not None:
                diff = round(min_p - old_min, 2)
                if diff > 0:
                    comment_parts.append(f"⬆ +{diff} BYN")
                elif diff < 0:
                    comment_parts.append(f"⬇ {diff} BYN")
                else:
                    comment_parts.append("без изменений")
            else:
                comment_parts.append("первая проверка")
        
        if result.get("on_sale"):
            comment_parts.append(f"🔥 скидка {result.get('discount', 0)}%")
        
        comment = ", ".join(comment_parts) if comment_parts else "нет данных"
        
        print(f"  {name}")
        print(f"  Ссылка: {product_url}")
        print(f"  Цены: {prices_url}")
        print(f"  Диапазон: {min_p} — {max_p} BYN ({result.get('offers_count', '?')} предложений) — {comment}")
        
        if result.get("top3"):
            print(f"  Топ-3:")
            for i, offer in enumerate(result["top3"], 1):
                sale_str = " 🔥 РАСПРОДАЖА" if offer.get("on_sale") else ""
                cb_str = f" | кэшбэк {offer['cashback']:.2f} BYN ({offer['cashback_pct']}%)" if offer.get("cashback") else ""
                dl_str = f" | самовывоз: {offer['delivery']}" if offer.get("delivery") else ""
                print(f"    {i}. {offer['shop']}: {offer['price']:.2f} BYN{sale_str}{cb_str}{dl_str}")
        
        if "onliner" not in data:
            data["onliner"] = {}
        data["onliner"][key] = {
            "name": name,
            "last_min_price": min_p,
            "last_max_price": max_p,
            "url": product_url,
            "prices_url": prices_url,
            "top3": result.get("top3", []),
        }
        
        changes.append(f"Onliner {key}: {min_p}—{max_p} BYN ({comment})")
    
    data["last_check"] = now
    save_prices(data)
    
    print(f"\n{'=' * 60}")
    print(f"ИТОГИ — {now}")
    print("=" * 60)
    for c in changes:
        print(f"  {c}")
    
    return changes


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch-and-update":
        fetch_and_update()
    else:
        print("Usage: python scripts/monitor.py fetch-and-update")
        sys.exit(1)