#!/usr/bin/env python3
"""Fetch and search Miaoda hot-rank case-analysis videos."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from typing import Any


APP_ORIGIN = "https://bytedance.feishuapp.com"
APP_ID = "app_179zmr1x048"
APP_BASE = f"{APP_ORIGIN}/app/{APP_ID}"
APP_PAGE = f"{APP_BASE}/hot-rank"
PAGE_ROUTE = f"/app/{APP_ID}/hot-rank"


def _read_response(resp: urllib.response.addinfourl) -> bytes:
    with resp:
        return resp.read()


class MiaodaClient:
    def __init__(self) -> None:
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        self.csrf_token = ""

    def bootstrap(self) -> None:
        req = urllib.request.Request(
            APP_PAGE,
            headers={
                "User-Agent": "Mozilla/5.0 Codex Miaoda Skill",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        html = _read_response(self.opener.open(req, timeout=30)).decode(
            "utf-8", errors="replace"
        )
        match = re.search(r'window\.csrfToken\s*=\s*"([^"]+)"', html)
        if not match:
            match = re.search(r'"csrfToken"\s*:\s*"([^"]+)"', html)
        if not match:
            raise RuntimeError("Could not find Miaoda CSRF token in app HTML")
        self.csrf_token = match.group(1)

    def api_get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.csrf_token:
            self.bootstrap()
        query = urllib.parse.urlencode(
            {k: v for k, v in (params or {}).items() if v not in (None, "")}
        )
        url = f"{APP_BASE}{path}"
        if query:
            url = f"{url}?{query}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 Codex Miaoda Skill",
                "Accept": "application/json",
                "X-Suda-Csrf-Token": self.csrf_token,
                "X-Page-Route": PAGE_ROUTE,
                "Referer": APP_PAGE,
            },
        )
        try:
            payload = _read_response(self.opener.open(req, timeout=30))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Miaoda API {exc.code}: {body}") from exc
        return json.loads(payload.decode("utf-8", errors="replace"))


def absolutize_media(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("/"):
        return APP_ORIGIN + value
    if isinstance(value, list):
        return [absolutize_media(item) for item in value]
    return value


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    normalized["app3sPicture"] = absolutize_media(normalized.get("app3sPicture"))
    normalized["appVideo"] = absolutize_media(normalized.get("appVideo"))
    return normalized


def compact_item(item: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "id",
        "rank",
        "videoTitle",
        "industry",
        "category",
        "productSubCategory",
        "creativeDirection",
        "xingchuanConsumptionLevel",
        "xingtuInfluencerNickname",
        "videoDuration",
        "videoType",
        "ctr",
        "cvr",
        "pvr",
        "pre3sScript",
        "bestsellerContentAnalysis",
        "openingHookLevel1",
        "openingHookLevel2",
        "videoLink",
        "app3sPicture",
        "appVideo",
    ]
    return {key: item.get(key) for key in keys if item.get(key) not in (None, "", [])}


def matches_keyword(item: dict[str, Any], keyword: str | None) -> bool:
    if not keyword:
        return True
    needle = keyword.lower()
    fields = [
        "videoTitle",
        "industry",
        "category",
        "productSubCategory",
        "creativeDirection",
        "xingtuInfluencerNickname",
        "pre3sScript",
        "bestsellerContentAnalysis",
        "asrText",
        "openingHookLevel1",
        "openingHookLevel2",
    ]
    return any(needle in str(item.get(field, "")).lower() for field in fields)


def pct(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return str(value)


def markdown_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No matching Miaoda hot-rank videos found."
    lines = [
        "| Rank | Title | Industry | Category | Direction | CTR | CVR | Link |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in items:
        title = str(item.get("videoTitle", "")).replace("|", "\\|")
        link = item.get("videoLink") or ""
        link_text = f"[Douyin]({link})" if link else ""
        lines.append(
            "| {rank} | {title} | {industry} | {category} | {direction} | {ctr} | {cvr} | {link} |".format(
                rank=item.get("rank", ""),
                title=title[:80],
                industry=item.get("industry", ""),
                category=item.get("category", ""),
                direction=item.get("creativeDirection", ""),
                ctr=pct(item.get("ctr")),
                cvr=pct(item.get("cvr")),
                link=link_text,
            )
        )
    return "\n".join(lines)


def fetch_videos(client: MiaodaClient, args: argparse.Namespace) -> list[dict[str, Any]]:
    params = {
        "industry": None if args.industry == "全部" else args.industry,
        "category": args.category,
        "productSubCategory": args.product_sub_category,
        "creativeDirection": args.creative_direction,
        "sortField": args.sort_field,
        "sortOrder": args.sort_order,
        "timeRange": args.time_range,
        "pageSize": args.page_size,
    }
    cursor = args.cursor
    results: list[dict[str, Any]] = []
    while len(results) < args.limit:
        if cursor:
            params["cursor"] = cursor
        data = client.api_get("/api/rank/videos", params)
        page_items = [normalize_item(item) for item in data.get("items", [])]
        for item in page_items:
            if matches_keyword(item, args.keyword):
                if args.details:
                    detail = client.api_get(
                        f"/api/rank/videos/{urllib.parse.quote(str(item['id']))}",
                        {"timeRange": args.time_range},
                    )
                    item.update(normalize_item(detail))
                results.append(compact_item(item))
                if len(results) >= args.limit:
                    break
        cursor = data.get("nextCursor") or data.get("cursor")
        if not cursor or not data.get("hasMore", bool(cursor)):
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch/search Miaoda 千川星选爆款内容榜单 case-analysis videos."
    )
    parser.add_argument("--time-range", default="7d", choices=["7d", "30d"])
    parser.add_argument("--industry", help="Top-level tab, e.g. 食品饮料 or 全部")
    parser.add_argument("--category", help="Second-level category from the app")
    parser.add_argument("--product-sub-category", help="Product subcategory filter")
    parser.add_argument("--creative-direction", help="Creative direction filter")
    parser.add_argument("--sort-field")
    parser.add_argument("--sort-order")
    parser.add_argument("--cursor")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--keyword", help="Local keyword search across title/analysis/script")
    parser.add_argument("--details", action="store_true", help="Fetch detail fields for each result")
    parser.add_argument("--detail", help="Fetch one video detail by id")
    parser.add_argument("--filters", action="store_true", help="Print filter options")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown table")
    args = parser.parse_args()

    client = MiaodaClient()
    try:
        if args.filters:
            output = client.api_get("/api/rank/filter-options", {"timeRange": args.time_range})
        elif args.detail:
            output = compact_item(
                normalize_item(
                    client.api_get(
                        f"/api/rank/videos/{urllib.parse.quote(args.detail)}",
                        {"timeRange": args.time_range},
                    )
                )
            )
        else:
            output = fetch_videos(client, args)
    except Exception as exc:
        print(f"miaoda_hot_rank.py: {exc}", file=sys.stderr)
        return 1

    if args.json or args.filters or args.detail:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(markdown_table(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
