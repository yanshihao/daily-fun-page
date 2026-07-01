#!/usr/bin/env python3
"""Collect China-friendly daily fun items for the static Daily Fun page.

标准库实现，适合 GitHub Actions 直接运行。内容策略：
- 优先中文来源/中文接口/RSS
- 仅保存标题、简短摘要和来源链接，不全文转载
- 外部源失败时使用内置中文趣味内容兜底
"""
from __future__ import annotations

import html
import json
import random
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
VERSIONS_DIR = DATA_DIR / "versions"
TODAY_JSON = DATA_DIR / "today.json"
ARCHIVE_INDEX = DATA_DIR / "archive.json"

USER_AGENT = "daily-fun-page/1.0 (+https://github.com/yanshihao/daily-fun-page)"
CHINA_TZ = ZoneInfo("Asia/Shanghai")

FALLBACK_FACTS = [
    {
        "emoji": "🧠",
        "source": "冷知识",
        "title": "为什么火锅越吃越香？",
        "summary": "热气、油脂、香辛料和社交氛围会一起放大食欲。很多时候，火锅好吃不只因为味道，也因为它天然适合热闹。",
        "url": "#",
    },
    {
        "emoji": "🌙",
        "source": "冷知识",
        "title": "古人也有“夜生活”",
        "summary": "宋代城市商业繁荣，夜市、瓦舍、勾栏都很热闹。很多古画和笔记里，都能看到当时城市生活的烟火气。",
        "url": "#",
    },
    {
        "emoji": "🍵",
        "source": "冷知识",
        "title": "茶叶曾经是硬通货",
        "summary": "茶在古代长期参与贸易和文化交流，从茶马古道到海上贸易，一片叶子连接过许多地方。",
        "url": "#",
    },
    {
        "emoji": "🚲",
        "source": "城市观察",
        "title": "最适合散步的城市，往往有很多小店",
        "summary": "街角小店、树荫、早餐摊和慢节奏，比单纯的大景点更容易让人记住一座城市。",
        "url": "#",
    },
]

QUOTES = [
    "今天也给自己留一点闲逛的时间。",
    "所谓有趣，就是在普通日子里多看见一层东西。",
    "如果不知道看什么，就从一个好问题开始。",
    "把每天的小发现存起来，生活会慢慢变厚。",
]

RSS_SOURCES = [
    {
        "name": "Solidot",
        "emoji": "🧪",
        "url": "https://www.solidot.org/index.rss",
        "summary_prefix": "中文科技社区 Solidot 的新鲜话题：",
    },
    {
        "name": "V2EX 最热",
        "emoji": "💬",
        "url": "https://www.v2ex.com/index.xml",
        "summary_prefix": "V2EX 社区正在讨论：",
    },
    {
        "name": "少数派",
        "emoji": "📱",
        "url": "https://sspai.com/feed",
        "summary_prefix": "来自少数派的效率、数字生活与应用观察：",
    },
]


def fetch_bytes(url: str, timeout: int = 20, headers: dict | None = None) -> bytes:
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, timeout: int = 20, headers: dict | None = None):
    return json.loads(fetch_bytes(url, timeout, headers=headers).decode("utf-8"))


def strip_html(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def clean(text: str, limit: int = 210) -> str:
    text = strip_html(str(text or ""))
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def parse_rss_datetime(text: str | None):
    if not text:
        return None
    try:
        return parsedate_to_datetime(text)
    except Exception:  # noqa: BLE001
        return None


def collect_rss_item(source: dict) -> dict | None:
    try:
        raw = fetch_bytes(source["url"])
        root = ET.fromstring(raw)
        channel_items = root.findall("./channel/item")
        atom_items = root.findall("{http://www.w3.org/2005/Atom}entry")
        candidates = []

        for item in channel_items:
            title = item.findtext("title")
            link = item.findtext("link")
            description = item.findtext("description") or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
            pub_date = parse_rss_datetime(item.findtext("pubDate"))
            if title and link:
                candidates.append((pub_date, title, link, description))

        for item in atom_items:
            title = item.findtext("{http://www.w3.org/2005/Atom}title")
            link_node = item.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.attrib.get("href") if link_node is not None else None
            description = item.findtext("{http://www.w3.org/2005/Atom}summary") or item.findtext("{http://www.w3.org/2005/Atom}content")
            updated = item.findtext("{http://www.w3.org/2005/Atom}updated")
            pub_date = None
            if updated:
                try:
                    pub_date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                except Exception:  # noqa: BLE001
                    pub_date = None
            if title and link:
                candidates.append((pub_date, title, link, description))

        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        _, title, link, description = candidates[0]
        return {
            "emoji": source["emoji"],
            "source": source["name"],
            "title": clean(title, 80),
            "summary": clean(f"{source['summary_prefix']}{description or title}", 210),
            "url": link,
        }
    except Exception as exc:  # noqa: BLE001
        print(f"RSS fetch failed [{source['name']}]: {exc}", file=sys.stderr)
        return None


BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "application/json,text/html,*/*",
}


def collect_baidu_hot_search(limit: int = 5) -> list[dict]:
    """Collect Baidu realtime hot-search topics from public hot board page."""
    url = "https://top.baidu.com/board?tab=realtime"
    try:
        raw = fetch_bytes(url, headers=BROWSER_HEADERS).decode("utf-8", "ignore")
        match = re.search(r"<!--s-data:(.*?)-->", raw, flags=re.S)
        if not match:
            return []
        data = json.loads(html.unescape(match.group(1)))
        cards = data.get("data", {}).get("cards", [])
        content = []
        for card in cards:
            if card.get("component") == "hotList":
                content = card.get("content") or []
                break

        items = []
        for entry in content[:limit]:
            title = clean(entry.get("query") or entry.get("word"), 80)
            if not title:
                continue
            score = entry.get("hotScore")
            score_text = f"，热度 {score}" if score else ""
            summary = clean((entry.get("desc") or f"百度实时热搜{score_text}。点击查看公开搜索结果。"), 210)
            items.append({
                "emoji": "🔎",
                "source": "百度热搜",
                "title": title,
                "summary": summary,
                "url": entry.get("rawUrl") or entry.get("url") or f"https://www.baidu.com/s?wd={urllib.parse.quote(title)}",
            })
        return items
    except Exception as exc:  # noqa: BLE001
        print(f"Baidu hot search fetch failed: {exc}", file=sys.stderr)
        return []


def collect_bilibili_popular(limit: int = 5) -> list[dict]:
    """Collect Bilibili popular videos from public API."""
    try:
        url = f"https://api.bilibili.com/x/web-interface/popular?ps={limit}&pn=1"
        data = fetch_json(url, headers=BROWSER_HEADERS)
        if data.get("code") != 0:
            return []
        items = []
        for entry in data.get("data", {}).get("list", [])[:limit]:
            title = clean(entry.get("title"), 80)
            if not title:
                continue
            owner = (entry.get("owner") or {}).get("name") or "UP 主"
            stat = entry.get("stat") or {}
            view = stat.get("view")
            view_text = f"播放 {view}" if view else "热门视频"
            desc = entry.get("desc") or "B站当前热门视频。"
            items.append({
                "emoji": "📺",
                "source": "B站热门",
                "title": title,
                "summary": clean(f"{owner} · {view_text} · {desc}", 210),
                "url": f"https://www.bilibili.com/video/av{entry.get('aid')}" if entry.get("aid") else "https://www.bilibili.com/v/popular/all",
            })
        return items
    except Exception as exc:  # noqa: BLE001
        print(f"Bilibili popular fetch failed: {exc}", file=sys.stderr)
        return []


def collect_zh_wikipedia_on_this_day(today: datetime) -> dict | None:
    """Use Chinese Wikipedia API to find today's month/day article snippet.

    中文维基没有和英文 feed 完全一致的稳定 on-this-day API。这里读取“M月D日”页面摘要，
    只展示摘要和链接，避免复制大量正文。
    """
    try:
        title = f"{today.month}月{today.day}日"
        encoded = urllib.parse.quote(title)
        url = f"https://zh.wikipedia.org/api/rest_v1/page/summary/{encoded}"
        data = fetch_json(url)
        extract = data.get("extract") or "历史上的今天，也许藏着一个值得顺手了解的小故事。"
        page_url = data.get("content_urls", {}).get("desktop", {}).get("page") or f"https://zh.wikipedia.org/wiki/{encoded}"
        return {
            "emoji": "📜",
            "source": "中文维基",
            "title": f"历史上的今天：{title}",
            "summary": clean(extract, 210),
            "url": page_url,
        }
    except Exception as exc:  # noqa: BLE001
        print(f"ZH Wikipedia fetch failed: {exc}", file=sys.stderr)
        return None


def collect_github_cn(today: datetime) -> dict | None:
    """Keep one open-source card, but prefer Chinese-language repos."""
    try:
        query = urllib.parse.quote("中文 in:name,description stars:>100 pushed:>2025-01-01")
        url = f"https://api.github.com/search/repositories?q={query}&sort=updated&order=desc&per_page=10"
        data = fetch_json(url)
        items = data.get("items") or []
        if not items:
            return None
        repo = random.choice(items[:5])
        description = repo.get("description") or "一个中文开源项目，适合顺手看看。"
        return {
            "emoji": "🧰",
            "source": "中文开源",
            "title": repo.get("full_name", "中文开源项目"),
            "summary": clean(f"⭐ {repo.get('stargazers_count', 0)} · {description}", 210),
            "url": repo.get("html_url"),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"GitHub CN fetch failed: {exc}", file=sys.stderr)
        return None


def build_archive_list(today: str, version_id: str | None = None) -> list[dict]:
    entries = []
    current_version_path = f"data/versions/{version_id}.json" if version_id else None

    # New format: each collection creates one timestamped version.
    # The currently loaded issue is intentionally excluded; the UI already has
    # a dedicated "最新 / 本期" button, and listing itself under "往期" is confusing.
    for path in sorted(VERSIONS_DIR.glob("*.json"), reverse=True):
        entry_path = f"data/versions/{path.name}"
        if entry_path == current_version_path:
            continue
        stem = path.stem
        date = stem[:10]
        time_part = stem[11:].replace("-", ":") if len(stem) > 11 else ""
        label = f"{date} {time_part}".strip()
        entries.append({"date": label, "path": entry_path})

    # Compatibility with older daily archive files. Skip today's stable archive
    # while rendering today's latest issue, because it is also the current page.
    for path in sorted(ARCHIVE_DIR.glob("*.json"), reverse=True):
        if path.stem == today and version_id:
            continue
        entries.append({"date": path.stem, "path": f"data/archive/{path.name}"})

    return entries[:30]


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(CHINA_TZ)
    today = now.strftime("%Y-%m-%d")
    version_id = now.strftime("%Y-%m-%d-%H-%M-%S")
    random.seed(today)

    items = []

    # 不强制登录的公开热门内容源，成功时优先展示。
    items.extend(collect_baidu_hot_search(limit=5))
    items.extend(collect_bilibili_popular(limit=5))

    wiki_item = collect_zh_wikipedia_on_this_day(now)
    if wiki_item:
        items.append(wiki_item)

    for source in RSS_SOURCES:
        item = collect_rss_item(source)
        if item:
            items.append(item)

    github_item = collect_github_cn(now)
    if github_item:
        items.append(github_item)

    # 中文兜底：确保每天至少有 5 条内容。
    fallback_pool = FALLBACK_FACTS[:]
    random.shuffle(fallback_pool)
    while len(items) < 5 and fallback_pool:
        items.append(fallback_pool.pop())

    items.append({
        "emoji": "✨",
        "source": "今日灵感",
        "title": "今天的小发现",
        "summary": random.choice(QUOTES),
        "url": "#",
    })

    seen = set()
    unique_items = []
    for item in items:
        title = item.get("title")
        if title and title not in seen:
            seen.add(title)
            unique_items.append(item)

    payload = {
        "date": today,
        "updated_at": now.isoformat(),
        "version_id": version_id,
        "locale": "zh-CN",
        "items": unique_items,
        "archive": build_archive_list(today, version_id),
    }

    version_path = VERSIONS_DIR / f"{version_id}.json"
    archive_path = ARCHIVE_DIR / f"{today}.json"
    version_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Keep the old daily path as a stable alias for the latest version of that day.
    archive_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    TODAY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ARCHIVE_INDEX.write_text(json.dumps(payload["archive"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Daily Fun generated: {version_id}, {len(unique_items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
