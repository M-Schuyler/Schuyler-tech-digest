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

AI + 市场交叉情报双 Bot 服务。主 Bot 负责每天一条综合简报，副 Bot 负责盘中异动和收盘提醒。

Run locally:

```bash
cd services/tech-news-digest
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py daily-brief --date 2026-04-23
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

Active workflows for `services/tech-news-digest/`:

- `.github/workflows/daily-ai-market-brief.yml`
- `.github/workflows/intraday-market-scan.yml`
- `.github/workflows/market-close-alert.yml`
