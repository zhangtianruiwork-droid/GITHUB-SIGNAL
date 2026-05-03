---
name: github-trending-scout
description: >
  Search and analyze the hottest open-source projects on GitHub daily. Fetches from both
  GitHub Trending page and GitHub Search API, merges and deduplicates results, then provides
  a summary of each project and a commercialization potential assessment. Use when user asks
  to "find trending repos", "GitHub trending", "hot open source projects", "每日GitHub热门",
  "开源项目推荐", "GitHub热榜", or wants to discover new popular repositories.
---

# GitHub Trending Scout

Fetch, merge, and analyze the hottest GitHub repos from two sources (Trending page + Search API), then output a concise report with project summaries and commercialization analysis.

## Workflow

### 1. Fetch Data

Run the bundled script to collect repos:

```bash
python scripts/fetch_trending.py --top 10
```

Supported flags:
- `--language <lang>` — filter by language (e.g. `python`, `rust`, `typescript`). Default: all.
- `--since daily|weekly|monthly` — trending page time range. Default: `daily`.
- `--days <n>` — API search lookback window in days. Default: `7`.
- `--top <n>` — number of repos to return. Default: `10`.

The script outputs JSON to stdout with merged, deduplicated repos sorted by stars descending.

If the user specifies a language or time range, pass the corresponding flags.

### 2. Analyze and Report

For each repo in the JSON output, produce a terminal-friendly report in Chinese with this structure:

```
## GitHub 热门开源项目日报 — {date}

数据来源: GitHub Trending + GitHub Search API
筛选条件: 语言={language}, 时间范围={since}

---

### 1. {owner}/{repo}  ⭐ {stars} | 🍴 {forks} | 📈 今日 +{stars_today}
- 语言: {language}
- 简介: {description — 用中文一两句话概括项目做什么}
- 核心功能: {列出 2-3 个核心功能点}
- 商业化前景: {评估商业化可能性，给出 ⬆高/➡中/⬇低 评级}
  - {1-2 句话说明理由: 目标市场、竞品、盈利模式可行性}

---
(repeat for each repo)
```

### 3. Commercialization Assessment Criteria

Evaluate each project on these dimensions:
- **Market demand** — Does it solve a real pain point with paying customers?
- **Competitive landscape** — Are there established commercial alternatives? Is there room for differentiation?
- **Monetization model** — Can it support SaaS, open-core, support/consulting, or marketplace models?
- **Community & traction** — Star growth velocity, contributor count, and ecosystem maturity.

Rating scale:
- ⬆ 高 — Clear path to revenue, strong market demand, viable business model
- ➡ 中 — Some commercial potential but faces significant competition or unclear monetization
- ⬇ 低 — Primarily community/educational value, hard to monetize directly

### 4. Output Rules

- Output directly to terminal in Chinese. Do not create files.
- Use markdown formatting for readability.
- If the script fails or returns empty results, inform the user and suggest trying with different parameters.
- If a repo description is in English, translate the summary to Chinese.
- Keep each project summary concise: no more than 4-5 lines per project.
