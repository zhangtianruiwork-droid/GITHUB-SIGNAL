#!/usr/bin/env python3
"""
GitHub Signal server — serves the frontend, trending data API, and DeepSeek AI proxy.
Run: python server.py
Then open http://localhost:8090
"""

import json
import sys
import os
import urllib.parse
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SKILL_SCRIPTS = Path(os.environ.get(
    "SKILL_SCRIPTS",
    Path.home() / ".claude" / "skills" / "github-trending-scout" / "scripts"
))
if SKILL_SCRIPTS.exists():
    sys.path.insert(0, str(SKILL_SCRIPTS))

from fetch_trending import fetch_trending, fetch_api_trending, merge_repos
from datetime import datetime, timezone

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"


def call_deepseek(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")
    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


class SignalHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SCRIPT_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/trending":
            self.handle_trending(parsed.query)
        elif parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/analyze":
            self.handle_analyze()
        else:
            self.send_error(404)

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def handle_trending(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        language = params.get("language", [""])[0]
        since = params.get("since", ["daily"])[0]
        domain = params.get("domain", [""])[0]
        days = int(params.get("days", ["7"])[0])
        top_n = int(params.get("top", ["10"])[0])

        top_n = max(1, min(top_n, 50))
        days = max(1, min(days, 30))
        if since not in ("daily", "weekly", "monthly"):
            since = "daily"

        print(f"[API] language={language or 'all'} since={since} domain={domain or 'all'} top={top_n}")

        trending = fetch_trending(language=language, since=since)
        api = fetch_api_trending(language=language, days=days, per_page=50)

        # Domain filtering: filter repos by topic keywords if domain is specified
        if domain:
            domain_keywords = DOMAIN_KEYWORDS.get(domain, [domain.lower()])
            trending = _filter_by_domain(trending, domain_keywords)
            api = _filter_by_domain(api, domain_keywords)

        merged = merge_repos(trending, api, top_n=top_n)

        self._send_json({
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "params": {"language": language or "all", "since": since, "domain": domain or "all", "top_n": top_n},
            "trending_count": len(trending),
            "api_count": len(api),
            "repos": merged,
        })

    def handle_analyze(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        repos = payload.get("repos", [])
        ui_lang = payload.get("lang", "en")
        if not repos:
            self._send_json({"error": "No repos"}, 400)
            return

        # Build a compact summary of repos for the AI prompt
        repo_lines = []
        for i, r in enumerate(repos):
            topics_str = ", ".join(r.get("topics", [])[:6])
            repo_lines.append(
                f"{i+1}. {r['full_name']} | {r.get('language','')} | "
                f"stars={r.get('stars',0)} forks={r.get('forks',0)} "
                f"stars_today={r.get('stars_today',0)} | "
                f"topics=[{topics_str}] | "
                f"desc: {r.get('description','')}"
            )
        repos_text = "\n".join(repo_lines)

        if ui_lang == "zh":
            system = (
                "你是一个开源项目分析专家。用户会给你一批GitHub热门项目的信息。"
                "请为每个项目输出：\n"
                "1. desc_zh: 中文项目简介（1-2句话）\n"
                "2. desc_en: 英文项目简介（1-2 sentences）\n"
                "3. biz_rating: 商业化潜力评级（高/中/低）\n"
                "4. biz_analysis: 商业化方向分析（2-3句话，包含可能的盈利模式、目标市场、竞品情况）\n"
                "严格按JSON数组格式输出，每个元素包含上述4个字段。不要输出其他内容。"
            )
        else:
            system = (
                "You are an open-source project analyst. The user gives you a batch of trending GitHub repos. "
                "For each repo output:\n"
                "1. desc_zh: Chinese project summary (1-2 sentences)\n"
                "2. desc_en: English project summary (1-2 sentences)\n"
                "3. biz_rating: Commercialization potential rating (High/Medium/Low)\n"
                "4. biz_analysis: Commercialization analysis (2-3 sentences: possible revenue models, target market, competitive landscape)\n"
                "Output strictly as a JSON array, each element with the 4 fields above. No other text."
            )

        # Split into batches of 8 to avoid token limits / 502 errors
        BATCH_SIZE = 8
        all_analyses = []
        for batch_start in range(0, len(repo_lines), BATCH_SIZE):
            batch = repo_lines[batch_start:batch_start + BATCH_SIZE]
            batch_text = "\n".join(batch)
            prompt = f"Analyze these {len(batch)} trending GitHub repos:\n\n{batch_text}"
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(repo_lines) + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"[AI] Batch {batch_num}/{total_batches} ({len(batch)} repos, lang={ui_lang})...")
            try:
                raw_resp = call_deepseek(prompt, system=system, max_tokens=3000)
                cleaned = raw_resp.strip()
                if cleaned.startswith("```"):
                    cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    cleaned = cleaned.strip()
                batch_analyses = json.loads(cleaned)
                all_analyses.extend(batch_analyses)
                print(f"[AI] Batch {batch_num} OK: {len(batch_analyses)} results")
            except json.JSONDecodeError as e:
                print(f"[AI] Batch {batch_num} JSON parse error: {e}\nRaw: {raw_resp[:300]}")
                # Fill with empty placeholders so indices stay aligned
                all_analyses.extend([{"desc_zh": "", "desc_en": "", "biz_rating": "", "biz_analysis": ""}] * len(batch))
            except Exception as e:
                print(f"[AI] Batch {batch_num} error: {e}")
                all_analyses.extend([{"desc_zh": "", "desc_en": "", "biz_rating": "", "biz_analysis": ""}] * len(batch))

        print(f"[AI] Done: {len(all_analyses)} total analyses")
        self._send_json({"analyses": all_analyses})

    def log_message(self, format, *args):
        msg = format % args
        if "/api/" in msg or "POST" in msg:
            print(f"[{self.log_date_time_string()}] {msg}")


# Domain keyword mapping for filtering
DOMAIN_KEYWORDS = {
    "ai":       ["ai", "ml", "machine-learning", "deep-learning", "llm", "gpt", "neural", "transformer", "nlp", "computer-vision", "diffusion", "agent"],
    "web":      ["web", "frontend", "backend", "react", "vue", "angular", "nextjs", "svelte", "django", "flask", "express", "api", "rest", "graphql"],
    "devtools":  ["devtools", "developer-tools", "cli", "terminal", "editor", "ide", "linter", "formatter", "build-tool", "bundler", "compiler", "debugger"],
    "infra":    ["infrastructure", "devops", "kubernetes", "docker", "cloud", "aws", "terraform", "ci-cd", "monitoring", "observability", "serverless"],
    "security": ["security", "cybersecurity", "encryption", "auth", "vulnerability", "pentest", "firewall", "privacy", "zero-trust"],
    "data":     ["data", "database", "analytics", "etl", "data-science", "visualization", "sql", "nosql", "streaming", "kafka", "spark"],
    "mobile":   ["mobile", "ios", "android", "react-native", "flutter", "swift", "kotlin", "app"],
    "blockchain": ["blockchain", "crypto", "web3", "ethereum", "solidity", "defi", "nft", "smart-contract"],
    "game":     ["game", "gamedev", "game-engine", "unity", "unreal", "godot", "3d", "graphics", "opengl", "vulkan"],
}


def _filter_by_domain(repos: list, keywords: list) -> list:
    """Filter repos whose topics, description, or name match any domain keyword."""
    result = []
    for r in repos:
        text = " ".join([
            r.get("description", "").lower(),
            r.get("full_name", "").lower(),
            " ".join(r.get("topics", [])),
        ])
        if any(kw in text for kw in keywords):
            result.append(r)
    return result


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    server = HTTPServer(("0.0.0.0", port), SignalHandler)
    print(f"""
    ╔══════════════════════════════════════════════╗
    ║   GITHUB.SIGNAL server running               ║
    ║   http://localhost:{port:<5}                     ║
    ║   DeepSeek AI: {DEEPSEEK_MODEL:<20}        ║
    ║   Press Ctrl+C to stop                       ║
    ╚══════════════════════════════════════════════╝
    """)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[shutdown] Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
