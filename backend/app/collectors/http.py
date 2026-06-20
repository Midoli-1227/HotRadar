from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urljoin

from ..schemas import HotItem, utc_now
from ..settings import HTTP_TIMEOUT_SECONDS
from ..sources import SourceConfig
from .base import CollectorError


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json,text/html,application/xml,text/xml,*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def strip_html(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text or None


def timestamp_to_iso(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return str(value)
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    return datetime.fromtimestamp(timestamp, UTC).isoformat(timespec="seconds")


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request_headers = DEFAULT_HEADERS.copy()
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        headers=request_headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        snippet = exc.read(1000).decode("utf-8", errors="replace")
        raise CollectorError(
            f"HTTP {exc.code} while fetching {url}",
            error_type="HttpError",
            http_status=exc.code,
            request_url=url,
            response_snippet=snippet,
        ) from exc
    except urllib.error.URLError as exc:
        raise CollectorError(
            f"Network error while fetching {url}: {exc.reason}",
            error_type="NetworkError",
            request_url=url,
        ) from exc
    except TimeoutError as exc:
        raise CollectorError(
            f"Timeout while fetching {url}",
            error_type="Timeout",
            request_url=url,
        ) from exc


def fetch_json(url: str, headers: dict[str, str] | None = None) -> Any:
    return json.loads(fetch_text(url, headers=headers))


class RSSCollector:
    def __init__(self, source: SourceConfig, feed_url: str):
        self.source = source
        self.feed_url = feed_url

    def fetch(self) -> list[HotItem]:
        raw = fetch_text(self.feed_url)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise CollectorError(
                f"Invalid RSS/Atom payload from {self.feed_url}: {exc}",
                error_type="ParseError",
                request_url=self.feed_url,
                response_snippet=raw[:1000],
            ) from exc

        items: list[HotItem] = []
        channel_items = root.findall(".//item")
        if channel_items:
            for index, node in enumerate(channel_items[:20], start=1):
                title = (node.findtext("title") or "").strip()
                link = (node.findtext("link") or "").strip()
                summary = strip_html(node.findtext("description"))
                published = node.findtext("pubDate")
                if title:
                    items.append(
                        HotItem(
                            source=self.source.id,
                            section=self.source.section,
                            rank=index,
                            title=html.unescape(title),
                            url=link,
                            summary=summary,
                            publishedAt=published,
                            fetchedAt=utc_now(),
                        )
                    )
            return items

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for index, node in enumerate(root.findall(".//atom:entry", ns)[:20], start=1):
            title = (node.findtext("atom:title", default="", namespaces=ns) or "").strip()
            link_node = node.find("atom:link", ns)
            link = link_node.attrib.get("href", "") if link_node is not None else ""
            summary = strip_html(
                node.findtext("atom:summary", default="", namespaces=ns)
                or node.findtext("atom:content", default="", namespaces=ns)
            )
            published = node.findtext("atom:published", default="", namespaces=ns)
            if title:
                items.append(
                    HotItem(
                        source=self.source.id,
                        section=self.source.section,
                        rank=index,
                        title=html.unescape(title),
                        url=link,
                        summary=summary,
                        publishedAt=published,
                        fetchedAt=utc_now(),
                    )
                )
        return items


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return html.unescape(re.sub(r"\s+", " ", strip_html(value) or "")).strip()


class AnthropicNewsCollector:
    url = "https://www.anthropic.com/news"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        raw = fetch_text(self.url, headers={"Referer": "https://www.anthropic.com/"})
        blocks = re.findall(r'(<a href="/news/[^"]+".*?</a>)', raw, flags=re.S)
        items: list[HotItem] = []
        seen: set[str] = set()

        for block in blocks:
            href_match = re.search(r'<a href="(/news/[^"]+)"', block)
            if not href_match:
                continue
            href = href_match.group(1)
            if href == "/news" or href in seen:
                continue

            title_match = re.search(
                r'<(?:h2|span)[^>]*(?:featuredTitle|title)[^>]*>(.*?)</(?:h2|span)>',
                block,
                flags=re.S,
            )
            title = _clean_text(title_match.group(1) if title_match else None)
            if not title:
                continue

            summary_match = re.search(r"<p[^>]*>(.*?)</p>", block, flags=re.S)
            date_match = re.search(r"<time[^>]*>(.*?)</time>", block, flags=re.S)
            subject_match = re.search(r'<span[^>]*(?:subject|caption bold)[^>]*>(.*?)</span>', block, flags=re.S)

            seen.add(href)
            items.append(
                HotItem(
                    source=self.source.id,
                    section=self.source.section,
                    rank=len(items) + 1,
                    title=title,
                    url=urljoin(self.url, href),
                    heat=_clean_text(subject_match.group(1) if subject_match else None) or None,
                    summary=_clean_text(summary_match.group(1) if summary_match else None) or None,
                    publishedAt=_clean_text(date_match.group(1) if date_match else None) or None,
                    fetchedAt=utc_now(),
                )
            )
            if len(items) >= 20:
                break

        if not items:
            raise CollectorError(
                "Could not parse Anthropic news page.",
                error_type="ParseError",
                request_url=self.url,
                response_snippet=raw[:1000],
            )
        return items


class HackerNewsCollector:
    topstories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    item_url_template = "https://hacker-news.firebaseio.com/v0/item/{story_id}.json"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        story_ids = fetch_json(self.topstories_url)
        if not isinstance(story_ids, list):
            raise CollectorError(
                "Invalid Hacker News topstories payload.",
                error_type="ParseError",
                request_url=self.topstories_url,
                response_snippet=str(story_ids)[:1000],
            )

        items: list[HotItem] = []
        for source_rank, story_id in enumerate(story_ids[:40], start=1):
            if len(items) >= 20:
                break

            item_url = self.item_url_template.format(story_id=story_id)
            hit = fetch_json(item_url)
            if not isinstance(hit, dict) or hit.get("deleted") or hit.get("dead"):
                continue

            title = hit.get("title") or ""
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            points = hit.get("score") or 0
            comments = hit.get("descendants") or 0
            if title:
                items.append(
                    HotItem(
                        source=self.source.id,
                        section=self.source.section,
                        rank=source_rank,
                        title=title,
                        url=url,
                        heat=f"{points} pts / {comments} comments",
                        author=hit.get("by"),
                        publishedAt=timestamp_to_iso(hit.get("time")),
                        fetchedAt=utc_now(),
                        extra={"id": story_id, "sourceRank": source_rank},
                    )
                )
        return items


class GitHubTrendingCollector:
    url = "https://github.com/trending"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        raw = fetch_text(self.url)
        repos: list[str] = []

        article_blocks = re.findall(
            r'<article\b[^>]*class="[^"]*\bBox-row\b[^"]*"[^>]*>(.*?)</article>',
            raw,
            flags=re.S,
        )
        for block in article_blocks:
            heading_match = re.search(r"<h2\b.*?</h2>", block, flags=re.S)
            ranking_scope = heading_match.group(0) if heading_match else block
            match = re.search(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', ranking_scope)
            if not match:
                continue
            repo = html.unescape(match.group(1))
            if repo not in repos:
                repos.append(repo)
            if len(repos) >= 20:
                break

        if not repos:
            raise CollectorError(
                "Could not parse repositories from GitHub Trending.",
                error_type="ParseError",
                request_url=self.url,
                response_snippet=raw[:1000],
            )

        return [
            HotItem(
                source=self.source.id,
                section=self.source.section,
                rank=index,
                title=repo,
                url=f"https://github.com/{repo}",
                fetchedAt=utc_now(),
                extra={"repo": repo},
            )
            for index, repo in enumerate(repos, start=1)
        ]


class ProductHuntFeedCollector(RSSCollector):
    feed_url = "https://www.producthunt.com/feed"

    def __init__(self, source: SourceConfig):
        super().__init__(source, self.feed_url)

    def fetch(self) -> list[HotItem]:
        items = super().fetch()
        for index, item in enumerate(items, start=1):
            item.rank = index
            item.extra["orderSource"] = "producthunt_atom_feed"
        return items


class WallstreetcnLiveCollector:
    url = "https://api-one-wscn.awtmt.com/apiv1/content/lives?channel=global-channel&client=pc&limit=20"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        payload = fetch_json(self.url)
        rows = payload.get("data", {}).get("items", [])
        items: list[HotItem] = []
        for index, row in enumerate(rows[:20], start=1):
            title = row.get("title") or ""
            content = row.get("content_text") or strip_html(row.get("content")) or ""
            url = row.get("uri") or self.source.homepageUrl
            heat_parts = []
            if row.get("global_channel_name"):
                heat_parts.append(str(row["global_channel_name"]))
            if row.get("comment_count"):
                heat_parts.append(f"{row['comment_count']} comments")
            if title:
                items.append(
                    HotItem(
                        source=self.source.id,
                        section=self.source.section,
                        rank=len(items) + 1,
                        title=title,
                        url=url,
                        heat=" / ".join(heat_parts) if heat_parts else None,
                        summary=content[:220] if content else None,
                        publishedAt=timestamp_to_iso(row.get("display_time")),
                        fetchedAt=utc_now(),
                        extra={"liveId": row.get("id")},
                    )
                )
        return items


class _AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        self._current = {"href": href, "text": ""}

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._current["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current is None:
            return
        text = " ".join(self._current["text"].split())
        if text:
            self.links.append({"href": self._current["href"], "text": text})
        self._current = None


class ClsHomeCollector:
    url = "https://www.cls.cn/"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        raw = fetch_text(self.url)
        parser = _AnchorCollector()
        parser.feed(raw)

        seen: set[str] = set()
        items: list[HotItem] = []
        for link in parser.links:
            href = link["href"]
            title = link["text"]
            if not re.fullmatch(r"/detail/\d+", href) or len(title) < 10:
                continue
            full_url = urljoin(self.url, href)
            if full_url in seen:
                continue
            seen.add(full_url)
            items.append(
                HotItem(
                    source=self.source.id,
                    section=self.source.section,
                    rank=len(items) + 1,
                    title=title,
                    url=full_url,
                    fetchedAt=utc_now(),
                    extra={"mode": "homepage_html"},
                )
            )
            if len(items) >= 20:
                break

        if not items:
            raise CollectorError(
                "Could not parse 财联社 homepage article links.",
                error_type="ParseError",
                request_url=self.url,
                response_snippet=raw[:1000],
            )
        return items


class ZhihuHotCollector:
    url = "https://api.zhihu.com/topstory/hot-lists/total?limit=20"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        payload = fetch_json(self.url)
        rows = payload.get("data", [])
        items: list[HotItem] = []
        for index, row in enumerate(rows[:20], start=1):
            target = row.get("target", {})
            title = target.get("title") or row.get("target", {}).get("question", {}).get("title") or ""
            target_id = target.get("id")
            url = (
                f"https://www.zhihu.com/question/{target_id}"
                if target_id
                else target.get("url") or target.get("link", {}).get("url") or self.source.homepageUrl
            )
            heat = row.get("detail_text") or row.get("label_area", {}).get("text")
            if title:
                items.append(
                    HotItem(
                        source=self.source.id,
                        section=self.source.section,
                        rank=index,
                        title=title,
                        url=url,
                        heat=heat,
                        summary=strip_html(target.get("excerpt")),
                        fetchedAt=utc_now(),
                    )
                )
        return items


class BilibiliPopularCollector:
    url = "https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        payload = fetch_json(self.url)
        rows = payload.get("data", {}).get("list", [])
        items: list[HotItem] = []
        for index, row in enumerate(rows[:20], start=1):
            title = row.get("title") or ""
            bvid = row.get("bvid")
            stat = row.get("stat", {})
            url = row.get("short_link_v2") or (f"https://www.bilibili.com/video/{bvid}" if bvid else "")
            heat = f"{stat.get('view', 0)} views / {stat.get('like', 0)} likes"
            if title:
                items.append(
                    HotItem(
                        source=self.source.id,
                        section=self.source.section,
                        rank=index,
                        title=title,
                        url=url,
                        heat=heat,
                        author=row.get("owner", {}).get("name"),
                        summary=row.get("desc"),
                        publishedAt=timestamp_to_iso(row.get("pubdate")),
                        fetchedAt=utc_now(),
                        extra={"bvid": bvid},
                    )
                )
        return items


class WeiboHotCollector:
    url = "https://weibo.com/ajax/side/hotSearch"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        payload = fetch_json(self.url, headers={"Referer": "https://weibo.com/"})
        rows = payload.get("data", {}).get("realtime", [])
        items: list[HotItem] = []
        for index, row in enumerate(rows[:20], start=1):
            title = row.get("word") or row.get("note") or ""
            if not title:
                continue
            items.append(
                HotItem(
                    source=self.source.id,
                    section=self.source.section,
                    rank=row.get("realpos") or index,
                    title=title,
                    url=f"https://s.weibo.com/weibo?q={quote(title)}",
                    heat=str(row.get("num")) if row.get("num") is not None else None,
                    summary=row.get("word_scheme") or row.get("note"),
                    fetchedAt=utc_now(),
                    extra={"label": row.get("label_name"), "flag": row.get("flag")},
                )
            )
        return items


class BaiduHotCollector:
    url = "https://top.baidu.com/board?tab=realtime"

    def __init__(self, source: SourceConfig):
        self.source = source

    def fetch(self) -> list[HotItem]:
        raw = fetch_text(self.url, headers={"Referer": "https://top.baidu.com/"})
        match = re.search(r"<!--s-data:(.*?)-->", raw, flags=re.S)
        if not match:
            raise CollectorError(
                "Could not find Baidu hot s-data payload.",
                error_type="ParseError",
                request_url=self.url,
                response_snippet=raw[:1000],
            )
        try:
            payload = json.loads(html.unescape(match.group(1)))
        except json.JSONDecodeError as exc:
            raise CollectorError(
                f"Could not parse Baidu hot s-data payload: {exc}",
                error_type="ParseError",
                request_url=self.url,
                response_snippet=match.group(1)[:1000],
            ) from exc

        cards = payload.get("data", {}).get("cards", [])
        rows: list[dict[str, Any]] = []
        for card in cards:
            if card.get("component") == "hotList" and isinstance(card.get("content"), list):
                rows = card["content"]
                break

        items: list[HotItem] = []
        for index, row in enumerate(rows[:20], start=1):
            title = row.get("word") or row.get("query") or ""
            if not title:
                continue
            items.append(
                HotItem(
                    source=self.source.id,
                    section=self.source.section,
                    rank=index,
                    title=title,
                    url=row.get("url") or row.get("rawUrl") or self.source.homepageUrl,
                    heat=row.get("hotScore"),
                    summary=row.get("desc"),
                    fetchedAt=utc_now(),
                    extra={"hotTag": row.get("hotTag"), "hotChange": row.get("hotChange")},
                )
            )
        return items


class UnsupportedCollector:
    def __init__(self, source: SourceConfig, reason: str):
        self.source = source
        self.reason = reason

    def fetch(self) -> list[HotItem]:
        raise CollectorError(
            self.reason,
            error_type="SourceUnavailable",
            request_url=self.source.homepageUrl,
        )
