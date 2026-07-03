# MEMORY.md

## Lessons Learned

### 2026-07-03: Web scraping SPA sites
- **Wildberries (and similar SPAs)**: When API endpoints return 403, use Playwright FIRST, not last.
- Playwright intercepts internal API calls (e.g. `/__internal/u-card/cards/v4/detail`) that aren't accessible via plain HTTP.
- WB card/catalog APIs are blocked for non-browser requests. The `search.wb.ru` API works for text search but not for direct product lookup by ID.
- Always prefer Playwright for sites that render content via JS.
- Order: Playwright → API → search engine fallback. Not the reverse.

## Preferences
- User language: Russian
- User timezone: Europe/Minsk (GMT+3)
- Interested in: Wildberries.by product prices, Onliner.by product prices

## Projects
- **web-radar**: Price checker for WB and Onliner. Source configs at `SOURCE_CONFIGS.md`.
  - WB: Playwright script `wb_pw2.py`, internal API `/__internal/u-card/cards/v4/detail?appType=1&curr=byn&dest=-8139704&spp=30`
  - Onliner: Open REST API at `catalog.api.onliner.by` and `shop.api.onliner.by`. Shop name field is `title`, not `name`.
  - Onliner: show top-3 offers with shop names and links, not just price range.

## Tracked Products
- WB 672171989: Орехи макадамия 1 кг в скорлупе 5а натуральные FASL
- WB 1164358226: Фисташки жареные солёные 1 кг (Vitaminka Candy)
- WB 28443957: Кедровые орехи в скорлупе неочищенные 900г (Сибирский кедр)
- Onliner 5908252006465: Finish Quantum Lemon 100 шт (капсулы для ПМ)