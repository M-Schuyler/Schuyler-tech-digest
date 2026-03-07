# 科技新闻自动抓取与摘要系统

一个每天自动抓取科技新闻、生成英中双语摘要，并可自动推送 Telegram 的 Python 项目。

支持站点：
- TechCrunch
- The Verge
- Wired

## 功能

1. 新闻抓取：通过 RSS 获取最新文章列表。  
2. 数据处理：提取标题、发布时间、原文链接、新闻内容。  
3. 双语摘要：每篇新闻生成 3 句英文摘要，并在每句下方给出对应中文翻译。  
   - 配置 `GEMINI_API_KEY` 时：优先使用 Gemini 2.5 Flash 生成英中摘要和关键词。  
   - 未配置 Gemini 但配置 `OPENAI_API_KEY` 时：使用 OpenAI 生成英中摘要和关键词。  
   - 两者都未配置时：自动使用免费翻译源（Google 网页接口，失败时回退 MyMemory）翻译英文摘要。  
4. 关键词提取：每篇新闻生成 3 个关键词。  
5. 数据存储：保存到 SQLite（`data/tech_news.db`）。  
6. 日报输出：生成“全站热点汇总”Markdown 报告（`reports/YYYY-MM-DD.md`，先英文后中文，不含来源字段），并给出 Top 趋势信号。  
7. Telegram 推送：自动发送日报到指定聊天。  
8. 云端自动运行：GitHub Actions 每日定时运行。

## 项目结构

```text
.
├── .github/workflows/daily-tech-news.yml
├── main.py
├── requirements.txt
├── data/
├── reports/
└── news_digest/
    ├── config.py
    ├── db.py
    ├── extractor.py
    ├── fetchers.py
    ├── models.py
    ├── notifier.py
    ├── pipeline.py
    ├── report.py
    └── summarizer.py
```

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

可选：指定日报日期（影响输出文件名）

```bash
python main.py --date 2026-03-07
```

## 环境变量

- `GEMINI_API_KEY`：可选。配置后优先使用 Gemini 2.5 Flash。
- `GEMINI_MODEL`：默认 `gemini-2.5-flash`。
- `OPENAI_API_KEY`：可选。配置后使用 OpenAI 直接生成高质量英中摘要。
- `OPENAI_MODEL`：默认 `gpt-4o-mini`。
- `MAX_ARTICLES_PER_SOURCE`：每个源最多抓取文章数，默认 `10`。
- `DAILY_HIGHLIGHT_COUNT`：日报中输出热点条数，默认 `6`。
- `REQUEST_TIMEOUT`：抓取超时秒数，默认 `20`。
- `FREE_TRANSLATION_TARGET`：免费翻译目标语言，默认 `zh-CN`。
- `FREE_TRANSLATION_TIMEOUT`：免费翻译请求超时秒数，默认 `15`。
- `TELEGRAM_BOT_TOKEN`：Telegram 机器人 Token。
- `TELEGRAM_CHAT_ID`：目标聊天 ID（个人或群组）。

示例：

```bash
export TELEGRAM_BOT_TOKEN="123456:abc..."
export TELEGRAM_CHAT_ID="123456789"
# 可选：开启 Gemini
export GEMINI_API_KEY="your_gemini_api_key"
python main.py
```

## SQLite 字段

`news` 表包含字段：
- `title`
- `source`
- `summary`
- `url`
- `date`

并额外保存 `keywords` 方便日报展示。

## 双语摘要格式（Markdown）

日报会输出“趋势信号 + 精简热点分点”两段，示例：

```text
# 今日科技圈新鲜事

## Key Signals (EN)
- Today's hottest directions are AI Models, Regulation & Policy, Platforms & Apps.
- [AI Models] Point 1
- [Regulation & Policy] Point 2

## 中文热点
- 今天最热方向集中在：AI 模型、监管与政策、平台与应用。
- [AI 模型] 要点 1
- [监管与政策] 要点 2
```

## 云端每日自动跑（GitHub Actions）

工作流文件已提供：
- `.github/workflows/daily-tech-news.yml`

默认调度：每天北京时间 08:00（UTC `0 0 * * *`）。

### 配置步骤

1. 把项目推到 GitHub 仓库。  
2. 进入仓库 `Settings -> Secrets and variables -> Actions`。  
3. 添加以下 Secrets：
   - 必填：`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`
   - 可选：`GEMINI_API_KEY`（优先，推荐）
   - 可选：`OPENAI_API_KEY`（备用）
4. 在 `Actions` 页面手动运行一次 `Daily Tech News Digest` 验证。  
5. 后续将每日自动执行并推送到 Telegram。

## 本地 cron（可选）

如果你仍想本地定时：

```cron
0 8 * * * cd /Users/chenshukai/Documents/New\ project && /Users/chenshukai/Documents/New\ project/.venv/bin/python main.py >> logs/cron.log 2>&1
```
