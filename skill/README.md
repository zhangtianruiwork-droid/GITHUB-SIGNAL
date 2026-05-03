# GitHub Trending Scout Skill

This folder contains the reusable **skill version** of the GitHub discovery workflow used by GITHUB.SIGNAL.

## Files

- `SKILL.md` — skill metadata and usage instructions
- `scripts/fetch_trending.py` — GitHub trending fetcher and merger

## Install

Copy this folder to:

```text
~/.claude/skills/github-trending-scout/
```

## Usage examples

```text
Find today's hottest GitHub repos
Show me trending Rust projects this week
每日 GitHub 热门开源项目推荐
帮我找今天最火的 AI 项目
```

## Purpose

Use the skill when you want an AI agent to:

- discover GitHub trending repos
- summarize what they do
- compare popularity signals
- estimate commercialization potential

This is the agent-friendly version of the same capability that powers the dashboard UI.
