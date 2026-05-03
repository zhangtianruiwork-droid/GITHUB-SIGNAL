# GITHUB.SIGNAL

[![MIT License](https://img.shields.io/badge/license-MIT-red.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/backend-Python-111111.svg)](#architecture)
[![Frontend](https://img.shields.io/badge/frontend-Single--file%20HTML-111111.svg)](#architecture)
[![Bilingual](https://img.shields.io/badge/language-EN%20%2F%20ZH-111111.svg)](#features)
[![AI Analysis](https://img.shields.io/badge/AI-DeepSeek%20V4%20Flash-111111.svg)](#features)

> **English**: An AI-powered GitHub trending intelligence dashboard with a constructivist / futurist visual identity, bilingual repo summaries, domain filters, and commercialization analysis.
>
> **中文**：一个 AI 驱动的 GitHub 热门项目情报看板，结合构成主义 / 未来主义视觉风格，提供中英双语简介、领域筛选和商业化分析。

## Overview | 项目简介

**GITHUB.SIGNAL** is built for developers, founders, indie hackers, and curious builders who want more than a plain trending list.

It turns GitHub hot projects into a signal dashboard: what is trending, what the project actually does, which domain it belongs to, and whether it may have real commercial potential.

**GITHUB.SIGNAL** 面向开发者、创业者、独立开发者，以及希望快速获取高质量开源信号的人群。它不只是展示“谁最火”，而是进一步回答：项目属于什么领域、核心价值是什么、是否具有商业化前景。

## Features | 功能亮点

- **Live GitHub trending aggregation**: combines GitHub Trending and Search API signals
- **Bilingual interface**: instant EN / ZH switching across the UI
- **Domain filtering**: AI, Web, DevTools, Infra, Security, Data, Mobile, Blockchain, Game Dev
- **AI summaries**: bilingual repo descriptions generated for readability and context
- **Commercialization analysis**: AI-assisted business potential rating and go-to-market direction hints
- **Theme switching**: dark + light presentation modes
- **Direct repo jump**: click any project and open the source repository immediately
- **Long-scroll reading experience**: optimized for browsing many projects instead of forcing a single-screen layout

- **实时热门聚合**：结合 GitHub Trending 与 Search API 的双数据源
- **双语界面切换**：支持中英文即时切换
- **领域筛选**：支持 AI、Web、开发工具、基础设施、安全、数据、移动端、区块链、游戏开发等方向
- **AI 双语简介**：自动生成更易读、更有上下文的项目摘要
- **商业化分析**：给出商业潜力评级与可能方向建议
- **亮色 / 暗色主题**：适应不同阅读偏好
- **仓库直达**：点击即可跳转到对应 GitHub 仓库
- **长滚动浏览体验**：更适合连续发现和比较多个项目

## Screenshot Section | 截图区

> This repository currently does **not** bundle screenshot assets. Recommended screenshots for the repo homepage:
>
> 1. **Overview / 总览页**: dark theme homepage with trending cards
> 2. **AI Analysis / AI 分析页**: cards showing bilingual summary + commercialization analysis
> 3. **Light Theme / 亮色主题**: same dataset under light mode

<img width="3828" height="1911" alt="image" src="https://github.com/user-attachments/assets/5b4e71f0-3139-40d1-aa9f-21cde0f54043" />
<img width="3828" height="1911" alt="image" src="https://github.com/user-attachments/assets/7249a1fa-7200-49ec-a424-72de5f6e2b4a" />


## Demo | 演示

### Local Demo

```bash
python server.py
```

Open in browser:

```text
http://localhost:8090
```

### AI Analysis Setup

Set your DeepSeek API key before using AI analysis:

```powershell
$env:DEEPSEEK_API_KEY="your_api_key"
python server.py
```

### Demo Flow

1. Open the dashboard
2. Choose language, domain, time range, and item count
3. Click `SCAN`
4. Click `AI ANALYZE`
5. Read bilingual summaries and commercialization suggestions

1. 打开仪表盘
2. 选择语言、领域、时间范围与项目数量
3. 点击 `SCAN`
4. 点击 `AI ANALYZE`
5. 查看双语简介与商业化建议

## Architecture | 架构说明

```text
Browser UI (index.html)
  -> /api/trending
      -> GitHub Trending page
      -> GitHub Search API
      -> merge + ranking + domain filter
  -> /api/analyze
      -> DeepSeek V4 Flash
      -> bilingual summary + business analysis
```

### Components

- **`index.html`**
  A single-file frontend with the full visual system, filtering controls, theme switching, bilingual UI, and card rendering.

- **`server.py`**
  A lightweight Python server that:
  - serves the frontend
  - aggregates trending repo data
  - filters by domain keywords
  - proxies AI analysis requests to DeepSeek
  - batches large AI jobs to reduce 502 errors

### Design Principles

- fast signal over noisy exploration
- visually memorable, not generic dashboard styling
- bilingual by default
- low setup cost
- easy to modify and self-host

- 强调高质量信号，而不是噪声式浏览
- 视觉风格鲜明，不做普通后台模板
- 默认支持双语
- 启动成本低
- 易于自定义与自托管

## Privacy & Security | 隐私与安全

- No API key is stored in this repository
- AI features require `DEEPSEEK_API_KEY` from environment variables
- Runtime logs are excluded from version control

- 仓库中不保存任何 API 密钥
- AI 功能通过环境变量 `DEEPSEEK_API_KEY` 提供凭据
- 运行日志不会提交到版本库

## Author | 作者

GitHub: **[@zhangtianruiwork-droid](https://github.com/zhangtianruiwork-droid)**

## License | 开源协议

This project is released under the **MIT License**.

本项目基于 **MIT License** 开源。
