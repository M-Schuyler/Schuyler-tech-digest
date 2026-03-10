# Workspace Overview

This repository is now organized as a small multi-project workspace.

## Structure

```text
apps/
  personal-website/        Next.js personal site
services/
  tech-news-digest/        Python RSS digest pipeline
playgrounds/
  reaction-speed-test/     Standalone static HTML mini-project
.github/workflows/         Shared automation and CI
```

## Projects

### `services/tech-news-digest`

Daily tech-news pipeline that fetches RSS articles, filters important stories, generates a bilingual briefing, stores results in SQLite, and can send the report to Telegram.

Run locally:

```bash
cd services/tech-news-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### `apps/personal-website`

Next.js personal website scaffold with projects and blog pages.

Run locally:

```bash
cd apps/personal-website
npm install
npm run dev
```

### `playgrounds/reaction-speed-test`

Standalone browser mini-project with no build step.

Open `playgrounds/reaction-speed-test/index.html` directly in a browser.

## Automation

The scheduled GitHub Actions job for the news digest still lives at `.github/workflows/daily-tech-news.yml`, but now runs from `services/tech-news-digest/`.
