#!/usr/bin/env python3
"""
Fetch trending GitHub repos from two sources:
1. GitHub Trending page (HTML scraping)
2. GitHub Search API (sorted by stars, recently created/updated)

Merges, deduplicates, and outputs JSON for Claude to analyze.
"""

import json
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# Source 1: Scrape github.com/trending
# ---------------------------------------------------------------------------

class TrendingParser(HTMLParser):
    """Minimal parser for GitHub Trending page."""

    def __init__(self):
        super().__init__()
        self.repos = []
        self._in_repo_link = False
        self._in_desc = False
        self._in_lang = False
        self._in_stars = False
        self._in_forks = False
        self._in_today_stars = False
        self._current = {}
        self._depth = 0
        self._article_depth = 0
        self._in_article = False
        self._text_buf = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        self._depth += 1

        if tag == "article" and "Box-row" in cls:
            self._in_article = True
            self._article_depth = self._depth
            self._current = {}

        if not self._in_article:
            return

        # Repo name link: <h2 class="h3 ..."><a href="/owner/repo">
        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"]
            # repo links look like /owner/repo (exactly two segments)
            parts = href.strip("/").split("/")
            if len(parts) == 2 and "full_name" not in self._current and parts[0] not in ("sponsors", "topics", "collections", "features", "settings"):
                self._current["full_name"] = "/".join(parts)
                self._current["url"] = f"https://github.com/{parts[0]}/{parts[1]}"
                self._in_repo_link = True
                self._text_buf = ""

        # Description: <p class="col-9 ...">
        if tag == "p" and ("col-9" in cls or "my-1" in cls):
            self._in_desc = True
            self._text_buf = ""

        # Language: <span itemprop="programmingLanguage">
        if tag == "span" and attrs_dict.get("itemprop") == "programmingLanguage":
            self._in_lang = True
            self._text_buf = ""

        # Stars / forks: <a class="... muted-link ..." href="/owner/repo/stargazers">
        if tag == "a" and "muted-link" in cls:
            href = attrs_dict.get("href", "")
            if "/stargazers" in href:
                self._in_stars = True
                self._text_buf = ""
            elif "/forks" in href or "/network" in href:
                self._in_forks = True
                self._text_buf = ""

        # Today stars: <span class="d-inline-block float-sm-right">
        if tag == "span" and "float-sm-right" in cls:
            self._in_today_stars = True
            self._text_buf = ""

    def handle_endtag(self, tag):
        if self._in_repo_link and tag == "a":
            self._in_repo_link = False

        if self._in_desc and tag == "p":
            self._current["description"] = self._text_buf.strip()
            self._in_desc = False

        if self._in_lang and tag == "span":
            self._current["language"] = self._text_buf.strip()
            self._in_lang = False

        if self._in_stars and tag == "a":
            self._current["stars"] = _parse_number(self._text_buf)
            self._in_stars = False

        if self._in_forks and tag == "a":
            self._current["forks"] = _parse_number(self._text_buf)
            self._in_forks = False

        if self._in_today_stars and tag == "span":
            self._current["stars_today"] = _parse_number(self._text_buf)
            self._in_today_stars = False

        if tag == "article" and self._in_article and self._depth == self._article_depth:
            self._in_article = False
            if "full_name" in self._current:
                self.repos.append(self._current)
            self._current = {}

        self._depth -= 1

    def handle_data(self, data):
        if self._in_repo_link or self._in_desc or self._in_lang or self._in_stars or self._in_forks or self._in_today_stars:
            self._text_buf += data


def _parse_number(text: str) -> int:
    """Extract a number from text like ' 1,234 ' or '567 stars today'."""
    cleaned = re.sub(r"[^\d]", "", text)
    return int(cleaned) if cleaned else 0


def fetch_trending(language: str = "", since: str = "daily") -> list[dict]:
    """Scrape GitHub Trending page. Returns list of repo dicts."""
    url = "https://github.com/trending"
    if language:
        url += f"/{urllib.parse.quote(language)}"
    url += f"?since={since}"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (github-trending-scout)"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        print(f"[warn] Failed to fetch trending page: {e}", file=sys.stderr)
        return []

    parser = TrendingParser()
    parser.feed(html)
    for r in parser.repos:
        r["source"] = "trending"
    return parser.repos


# ---------------------------------------------------------------------------
# Source 2: GitHub Search API
# ---------------------------------------------------------------------------

def fetch_api_trending(language: str = "", days: int = 7, per_page: int = 30) -> list[dict]:
    """Use GitHub Search API to find repos with most stars created/pushed recently."""
    since_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    q_parts = [f"pushed:>{since_date}", "stars:>50"]
    if language:
        q_parts.append(f"language:{language}")
    query = " ".join(q_parts)

    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page={per_page}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "github-trending-scout",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[warn] Failed to fetch from GitHub API: {e}", file=sys.stderr)
        return []

    repos = []
    for item in data.get("items", []):
        repos.append({
            "full_name": item["full_name"],
            "url": item["html_url"],
            "description": item.get("description") or "",
            "language": item.get("language") or "",
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "stars_today": 0,  # API doesn't provide daily stars
            "created_at": item.get("created_at", ""),
            "topics": item.get("topics", []),
            "license": (item.get("license") or {}).get("spdx_id", ""),
            "source": "api",
        })
    return repos


# ---------------------------------------------------------------------------
# Merge & deduplicate
# ---------------------------------------------------------------------------

def _trending_score(repo: dict) -> float:
    """Score a repo by how 'trending' it is, not just absolute popularity.

    Factors:
    - Trending page presence (strong signal of current momentum)
    - Stars today (direct velocity metric from trending page)
    - Recency bonus (newer repos with high stars are more interesting)
    - Absolute stars (tiebreaker, log-scaled to avoid mega-repo dominance)
    """
    import math

    score = 0.0

    # Source bonus: trending page repos get a big boost
    source = repo.get("source", "")
    if source == "trending":
        score += 500
    elif source == "both":
        score += 600  # on both sources = very hot

    # Daily star velocity (strongest signal when available)
    stars_today = repo.get("stars_today", 0)
    score += stars_today * 5

    # Recency bonus: repos created in the last year get a boost
    created = repo.get("created_at", "")
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
            if age_days <= 30:
                score += 300  # brand new
            elif age_days <= 90:
                score += 200
            elif age_days <= 365:
                score += 100
            elif age_days <= 730:
                score += 30
        except (ValueError, TypeError):
            pass

    # Absolute stars as tiebreaker (log-scaled)
    stars = repo.get("stars", 0)
    if stars > 0:
        score += math.log2(stars) * 5  # 1000 stars -> ~50, 100k -> ~85

    return score


def merge_repos(trending: list[dict], api: list[dict], top_n: int = 10) -> list[dict]:
    """Merge two lists, deduplicate by full_name, rank by trending score, return top N."""
    seen = {}
    for r in trending:
        key = r["full_name"].lower()
        if key not in seen:
            seen[key] = r
        else:
            existing = seen[key]
            existing["source"] = "both"
            for k in ("topics", "created_at", "license"):
                if k in r and r[k] and not existing.get(k):
                    existing[k] = r[k]
            if r.get("stars_today", 0) > existing.get("stars_today", 0):
                existing["stars_today"] = r["stars_today"]

    for r in api:
        key = r["full_name"].lower()
        if key not in seen:
            seen[key] = r
        else:
            existing = seen[key]
            existing["source"] = "both"
            for k in ("topics", "created_at", "license"):
                if k in r and r[k] and not existing.get(k):
                    existing[k] = r[k]
            if r.get("stars", 0) > existing.get("stars", 0):
                existing["stars"] = r["stars"]

    for r in seen.values():
        r["_score"] = round(_trending_score(r), 1)

    merged = sorted(seen.values(), key=lambda x: x["_score"], reverse=True)
    return merged[:top_n]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch GitHub trending repos")
    parser.add_argument("--language", default="", help="Filter by programming language")
    parser.add_argument("--since", default="daily", choices=["daily", "weekly", "monthly"],
                        help="Trending time range")
    parser.add_argument("--days", type=int, default=7, help="API search lookback days")
    parser.add_argument("--top", type=int, default=10, help="Number of repos to return")
    args = parser.parse_args()

    trending = fetch_trending(language=args.language, since=args.since)
    api = fetch_api_trending(language=args.language, days=args.days, per_page=30)
    merged = merge_repos(trending, api, top_n=args.top)

    output = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "params": {
            "language": args.language or "all",
            "since": args.since,
            "api_days": args.days,
            "top_n": args.top,
        },
        "trending_count": len(trending),
        "api_count": len(api),
        "repos": merged,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
