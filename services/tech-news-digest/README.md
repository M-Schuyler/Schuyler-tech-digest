# Tech News RSS Briefing System

Project location in this workspace: `services/tech-news-digest/`

A daily tech-news pipeline that fetches RSS articles, removes duplicates, filters high-impact topics via AI classification, and outputs a bilingual (EN/ZH) Daily Tech Briefing.

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
8. Output **Daily Tech Briefing** with maximum 10 items.
9. Send report to Telegram.

## Output Format

Generated file: `reports/YYYY-MM-DD.md`

```text
# 🗞️ 今日科技快报（中文一眼版）

- 📅 日期：2026-03-08
- 🧾 入选新闻：10 条

## 🧭 一眼看懂
- 🔥 热门方向：🧠人工智能 4条、🏢科技大厂 3条、💾芯片 2条
- 🧠 今日结论：AI 仍是主线，大厂动作频繁。
- 📈 最高热度：88 / 100

## ⭐ 最值得关注（Top 3）
1. 🧠人工智能：...
2. 🏢科技大厂：...
3. 💾芯片：...

## 💼 融资与公司动作
- 🚀创业融资：...

## ⚙️ 产业与技术突破
- 🤖机器人：...
```

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
python main.py
```

Optional date:

```bash
python main.py --date 2026-03-08
```

## Environment Variables

- `GEMINI_API_KEY` (recommended)
- `GEMINI_MODEL` (default: `gemini-2.5-flash`)
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
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## GitHub Actions (Daily Cloud Run)

Workflow file: `../../.github/workflows/daily-tech-news.yml`

- Schedule: daily at `08:00` Asia/Shanghai (`0 0 * * *` UTC).
- Also supports manual trigger (`workflow_dispatch`).

Required GitHub Secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional Secrets:

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`

## Database

SQLite DB: `data/tech_news.db`

Table `news` fields:

- `title`
- `source`
- `summary`
- `url`
- `date`
- `keywords` (stores category)
