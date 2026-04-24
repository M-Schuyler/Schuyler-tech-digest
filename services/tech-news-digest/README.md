# AI + Market Intelligence Bot System

Project location in this workspace: `services/tech-news-digest/`

A daily intelligence pipeline with two product surfaces:

- Main bot: one daily AI + 科技 + 市场交叉情报简报
- Side bot: intraday anomaly alerts + close summary for 美股 / 币圈核心资产

## Sources

- TechCrunch: `https://techcrunch.com/feed/`
- The Verge: `https://www.theverge.com/rss/index.xml`
- Wired: `https://www.wired.com/feed/rss`
- MIT Technology Review: `https://www.technologyreview.com/feed/`
- Ars Technica: `http://feeds.arstechnica.com/arstechnica/index`

## Pipeline

1. Fetch articles from RSS feeds.
2. Remove duplicates (URL normalization + title dedupe).
3. Fast title pre-filter to avoid low-signal extraction.
4. AI classify + filter important tech news.
5. Keep only categories:
   - `AI`
   - `Robotics`
   - `Chips`
   - `Big Tech`
   - `Startups`
6. Exclude low-signal content:
   - phone reviews
   - gaming
   - gadget reviews
   - entertainment
   - opinion/editorials
7. Generate for each selected article:
   - title
   - English summary (2 sentences)
   - Chinese summary (2 sentences)
8. Compose the main bot brief and side bot alerts.
9. Send formatted cards and text to Telegram.

## AI Priority

Summarization/classification backend priority:

1. Gemini (`GEMINI_API_KEY`)
2. OpenAI (`OPENAI_API_KEY`)
3. Local heuristic + free translation fallback

## Setup

```bash
cd services/tech-news-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

New jobs:

```bash
python main.py daily-brief --date 2026-04-23
python main.py intraday-scan --now 2026-04-23T10:00:00-04:00
python main.py close-alert --now 2026-04-23T16:30:00-04:00
```

## Environment Variables

- `GEMINI_API_KEY` (recommended)
- `GEMINI_MODEL` (default: `3.1-flash-preview`)
- `OPENAI_API_KEY` (optional fallback)
- `OPENAI_MODEL` (default: `gpt-4o-mini`)
- `MAX_ARTICLES_PER_SOURCE` (default: `20`)
- `MAX_BRIEFING_ITEMS` (default: `10`)
- `MIN_IMPORTANCE_SCORE` (default: `55`)
- `REQUEST_TIMEOUT` (default: `20`)
- `FREE_TRANSLATION_TARGET` (default: `zh-CN`)
- `FREE_TRANSLATION_TIMEOUT` (default: `8`)
- `MAX_EXTRACTION_ATTEMPTS` (default: `max(30, MAX_BRIEFING_ITEMS*6)`)
- `TARGET_CANDIDATE_POOL` (default: `max(MAX_BRIEFING_ITEMS*3, MAX_BRIEFING_ITEMS)`)
- `TELEGRAM_BOT_TOKEN_MAIN`
- `TELEGRAM_CHAT_ID_MAIN`
- `TELEGRAM_BOT_TOKEN_SIDE`
- `TELEGRAM_CHAT_ID_SIDE`
- `STATE_DB_URL`
- `STATE_DB_AUTH_TOKEN`
- `MARKET_PROVIDER` (`yahoo` or `twelvedata`)
- `TWELVEDATA_API_KEY` (required when `MARKET_PROVIDER=twelvedata`)
- `MARKET_SYMBOL_BUDGET` (optional override; defaults to `8` for `twelvedata`)
- `INTRADAY_INTERVAL_MINUTES`
- `MAX_INTRADAY_ALERTS_PER_DAY`
- `VOLUME_BASELINE_LOOKBACK_DAYS`
- `VOLUME_BASELINE_MULTIPLIER`
- `CHART_DEFAULT_SYMBOLS`

## Market Data Provider Notes

- `MARKET_PROVIDER=yahoo`
  - zero setup
  - useful for smoke runs
  - not reliable enough for production intraday alerts
- `MARKET_PROVIDER=twelvedata`
  - recommended production default
  - one provider covers US stocks and crypto
  - provider only fetches the symbols each call actually needs
  - default symbol budget is capped at `8`, so the free tier does not try to monitor all `11` symbols every 15 minutes
  - close alerts reuse bars already stored by intraday scans instead of re-spending credits at `16:30` New York time

## GitHub Actions

- `../../.github/workflows/daily-ai-market-brief.yml`
- `../../.github/workflows/intraday-market-scan.yml`
- `../../.github/workflows/market-close-alert.yml`

Schedules:

- Main brief: daily at `08:00` Asia/Shanghai
- Intraday scan: every 15 minutes during trading windows
- Close alert: aligned to `16:30` America/New_York

Required GitHub Secrets:

- `TELEGRAM_BOT_TOKEN_MAIN`
- `TELEGRAM_CHAT_ID_MAIN`
- `TELEGRAM_BOT_TOKEN_SIDE`
- `TELEGRAM_CHAT_ID_SIDE`
- `STATE_DB_URL`
- `STATE_DB_AUTH_TOKEN`

Optional Secrets:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `TWELVEDATA_API_KEY` (required only when `MARKET_PROVIDER=twelvedata`)

Recommended GitHub Variables:

- `MARKET_PROVIDER`
  - set to `yahoo` for zero-setup smoke runs
  - set to `twelvedata` for production intraday / close jobs

## State Storage

Primary state lives in Turso/libSQL via:

- `STATE_DB_URL`
- `STATE_DB_AUTH_TOKEN`

Local smoke runs can still use:

- `STATE_DB_LOCAL_PATH`
