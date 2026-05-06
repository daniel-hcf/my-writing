import hashlib
import html
import json
import logging
import re
import smtplib
import threading
import time
import sqlite3
from datetime import datetime
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from .db import connect, get_config, set_config
from .providers import get_text_provider
from .secret_store import decrypt_secret, encrypt_secret, is_encrypted
from .services import parse_json_loose

log = logging.getLogger(__name__)

CHANNEL_SOCIAL = "social"
CHANNEL_STORY = "story"
CHANNEL_LABELS = {
    CHANNEL_SOCIAL: "当前社会热点",
    CHANNEL_STORY: "故事素材雷达",
}
MASK = "***"

SOURCE_PACKS = [
    {
        "id": "social",
        "name": "热点雷达包",
        "description": "GitHub 热点、微博/百度/知乎热搜，用于观察当下议题和技术风向。",
        "sources": [
            {"name": "GitHub Trending", "url": "https://rsshub.app/github/trending/daily/any/any", "channel": CHANNEL_SOCIAL},
            {"name": "微博热搜", "url": "https://rsshub.app/weibo/search/hot/fulltext", "channel": CHANNEL_SOCIAL},
            {"name": "百度热搜", "url": "https://rsshub.app/baidu/top", "channel": CHANNEL_SOCIAL},
            {"name": "知乎热榜", "url": "https://rsshub.app/zhihu/hot", "channel": CHANNEL_SOCIAL},
            {"name": "中新网国际新闻", "url": "https://www.chinanews.com.cn/rss/world.xml", "channel": CHANNEL_SOCIAL},
            {"name": "中新网社会新闻", "url": "https://www.chinanews.com.cn/rss/society.xml", "channel": CHANNEL_SOCIAL},
        ],
    },
    {
        "id": "story",
        "name": "Reddit故事素材包",
        "description": "怪谈、危险遭遇、未解悬案、关系冲突和秘密 confession。",
        "sources": [
            {"name": "Reddit NoSleep", "url": "https://www.reddit.com/r/nosleep/.rss", "channel": CHANNEL_STORY},
            {"name": "Reddit LetsNotMeet", "url": "https://www.reddit.com/r/LetsNotMeet/.rss", "channel": CHANNEL_STORY},
            {"name": "Reddit UnresolvedMysteries", "url": "https://www.reddit.com/r/UnresolvedMysteries/.rss", "channel": CHANNEL_STORY},
            {"name": "Reddit Relationships", "url": "https://www.reddit.com/r/relationships/.rss", "channel": CHANNEL_STORY},
            {"name": "Reddit Confession", "url": "https://www.reddit.com/r/confession/.rss", "channel": CHANNEL_STORY},
        ],
    },
]


def _basic_pack() -> dict:
    social = SOURCE_PACKS[0]["sources"][:5]
    story = SOURCE_PACKS[1]["sources"][:6]
    return {
        "id": "basic",
        "name": "双频道基础包",
        "description": "同时导入社会热点和故事素材的精简推荐源。",
        "sources": [*social, *story],
    }


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def list_source_packs() -> list[dict]:
    packs = [*SOURCE_PACKS, _basic_pack()]
    return [
        {
            "id": pack["id"],
            "name": pack["name"],
            "description": pack["description"],
            "sources": pack["sources"],
        }
        for pack in packs
    ]


def _find_pack(pack_id: str) -> dict:
    for pack in list_source_packs():
        if pack["id"] == pack_id:
            return pack
    raise ValueError(f"unknown source pack: {pack_id}")


def create_source(name: str, url: str, channel: str, enabled: bool = True) -> dict:
    if channel not in CHANNEL_LABELS:
        raise ValueError(f"unknown channel: {channel}")
    name = name.strip()
    url = url.strip()
    if not name or not url:
        raise ValueError("name and url are required")
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO rss_sources (name, url, channel, enabled, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, url, channel, 1 if enabled else 0, _now()),
        )
        return source_row_to_dict(conn.execute("SELECT * FROM rss_sources WHERE id = ?", (cur.lastrowid,)).fetchone())


def update_source(source_id: int, payload: dict) -> dict:
    current = get_source(source_id)
    if not current:
        raise ValueError("source not found")
    name = (payload.get("name") or current["name"]).strip()
    url = (payload.get("url") or current["url"]).strip()
    channel = payload.get("channel") or current["channel"]
    enabled = payload.get("enabled", current["enabled"])
    if channel not in CHANNEL_LABELS:
        raise ValueError(f"unknown channel: {channel}")
    with connect() as conn:
        conn.execute(
            """
            UPDATE rss_sources
            SET name = ?, url = ?, channel = ?, enabled = ?
            WHERE id = ?
            """,
            (name, url, channel, 1 if enabled else 0, source_id),
        )
    return get_source(source_id)


def delete_source(source_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM materials WHERE source_id = ?", (source_id,))
        conn.execute("DELETE FROM rss_sources WHERE id = ?", (source_id,))


def get_source(source_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM rss_sources WHERE id = ?", (source_id,)).fetchone()
    return source_row_to_dict(row) if row else None


def list_sources() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM rss_sources ORDER BY channel, name").fetchall()
    return [source_row_to_dict(row) for row in rows]


def import_source_pack(pack_id: str) -> dict:
    pack = _find_pack(pack_id)
    imported = 0
    skipped = 0
    imported_sources = []
    with connect() as conn:
        for source in pack["sources"]:
            existing = conn.execute("SELECT id FROM rss_sources WHERE url = ?", (source["url"],)).fetchone()
            if existing:
                skipped += 1
                continue
            cur = conn.execute(
                """
                INSERT INTO rss_sources (name, url, channel, enabled, created_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (source["name"], source["url"], source["channel"], _now()),
            )
            imported += 1
            imported_sources.append(
                source_row_to_dict(conn.execute("SELECT * FROM rss_sources WHERE id = ?", (cur.lastrowid,)).fetchone())
            )
    return {"pack": pack, "imported": imported, "skipped": skipped, "sources": imported_sources}


def source_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "channel": row["channel"],
        "channelLabel": CHANNEL_LABELS.get(row["channel"], row["channel"]),
        "enabled": bool(row["enabled"]),
        "lastCheckedAt": row["last_checked_at"],
        "lastError": row["last_error"],
        "createdAt": row["created_at"],
    }


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node: ElementTree.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in list(node):
        if _local_name(child.tag) in wanted and child.text:
            return child.text.strip()
    return ""


def _entry_link(node: ElementTree.Element) -> str:
    for child in list(node):
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return href.strip()
        if child.text:
            return child.text.strip()
    return ""


def _normalize_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return value.strip()


def parse_feed_xml(xml_text: str) -> list[dict]:
    root = ElementTree.fromstring(xml_text)
    entries = [node for node in root.iter() if _local_name(node.tag) in {"item", "entry"}]
    items = []
    for entry in entries:
        title = _strip_html(_child_text(entry, "title"))
        url = _entry_link(entry)
        summary = _strip_html(_child_text(entry, "description", "summary", "content", "encoded"))
        published_at = _normalize_date(_child_text(entry, "pubDate", "published", "updated", "date"))
        if not title or not url:
            continue
        items.append({"title": title, "summary": summary, "url": url, "published_at": published_at})
    return items


async def fetch_source(source: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.get(source["url"])
            response.raise_for_status()
        items = parse_feed_xml(response.text)
        inserted = 0
        for item in items:
            if upsert_material(source["id"], source["channel"], item):
                inserted += 1
        _mark_source_checked(source["id"], None)
        return {"source": source, "fetched": len(items), "inserted": inserted, "error": None}
    except Exception as exc:
        _mark_source_checked(source["id"], str(exc))
        return {"source": source, "fetched": 0, "inserted": 0, "error": str(exc)}


async def fetch_enabled_sources() -> dict:
    sources = [source for source in list_sources() if source["enabled"]]
    results = [await fetch_source(source) for source in sources]
    return {
        "sources": results,
        "fetched": sum(item["fetched"] for item in results),
        "inserted": sum(item["inserted"] for item in results),
        "errors": [item for item in results if item["error"]],
    }


def _mark_source_checked(source_id: int, error: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE rss_sources SET last_checked_at = ?, last_error = ? WHERE id = ?",
            (_now(), error, source_id),
        )


def _material_hash(title: str, summary: str, url: str) -> str:
    value = "\n".join([title.strip(), summary.strip(), url.strip()])
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def upsert_material(source_id: int, channel: str, item: dict) -> int | None:
    title = (item.get("title") or "").strip()
    url = (item.get("url") or "").strip()
    if not title or not url:
        return None
    summary = (item.get("summary") or "").strip()
    published_at = (item.get("published_at") or "").strip()
    content_hash = _material_hash(title, summary, url)
    with connect() as conn:
        existing = conn.execute("SELECT id FROM materials WHERE url = ?", (url,)).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            """
            INSERT INTO materials
              (source_id, channel, title, summary, url, published_at, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source_id, channel, title, summary, url, published_at, content_hash, _now()),
        )
        return cur.lastrowid


def list_materials(channel: str | None = None, limit: int = 100) -> list[dict]:
    sql = """
        SELECT m.*, s.name AS source_name
        FROM materials m
        INNER JOIN rss_sources s ON s.id = m.source_id
    """
    params: list[Any] = []
    if channel:
        sql += " WHERE m.channel = ?"
        params.append(channel)
    sql += " ORDER BY m.id DESC LIMIT ?"
    params.append(limit)
    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [material_row_to_dict(row) for row in rows]


def get_material(material_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT m.*, s.name AS source_name
            FROM materials m
            INNER JOIN rss_sources s ON s.id = m.source_id
            WHERE m.id = ?
            """,
            (material_id,),
        ).fetchone()
    return material_row_to_dict(row) if row else None


def _loads_json(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _short_text(value: str | None, limit: int = 120) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def material_row_to_dict(row: sqlite3.Row) -> dict:
    keywords = _loads_json(row["keywords"], [])
    display_summary = row["ai_summary"] or _short_text(row["summary"])
    return {
        "id": row["id"],
        "sourceId": row["source_id"],
        "sourceName": row["source_name"] if "source_name" in row.keys() else None,
        "channel": row["channel"],
        "channelLabel": CHANNEL_LABELS.get(row["channel"], row["channel"]),
        "title": row["title"],
        "summary": row["summary"],
        "displaySummary": display_summary,
        "url": row["url"],
        "publishedAt": row["published_at"],
        "aiCategory": row["ai_category"],
        "aiSummary": row["ai_summary"],
        "aiReason": row["ai_reason"],
        "fictionFit": row["fiction_fit"],
        "fictionAngle": row["fiction_angle"],
        "keywords": keywords,
        "deepDive": _loads_json(row["deep_dive"], None),
        "storyIdeas": _loads_json(row["story_ideas"], None),
        "createdAt": row["created_at"],
    }


def _materials_for_brief(date: str, per_channel_limit: int = 12) -> list[dict]:
    materials = []
    with connect() as conn:
        for channel in (CHANNEL_SOCIAL, CHANNEL_STORY):
            rows = conn.execute(
                """
                SELECT m.*, s.name AS source_name
                FROM materials m
                INNER JOIN rss_sources s ON s.id = m.source_id
                WHERE substr(m.created_at, 1, 10) = ?
                  AND m.channel = ?
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (date, channel, per_channel_limit),
            ).fetchall()
            materials.extend(material_row_to_dict(row) for row in rows)
    return materials


def _brief_system_prompt() -> str:
    return (
        "你是用户的 AI 编辑部。请把 RSS 素材整理成双频道每日简报：当前社会热点和故事素材雷达。"
        "无论 RSS 原文是中文、英文还是其他语言，你给用户看的所有字段都必须使用自然中文；"
        "英文标题和摘要要先理解并翻译成中文，再进行分类、摘要和创作转化。"
        "必须只输出合法 JSON，不要 Markdown。"
    )


def _brief_user_prompt(materials: list[dict]) -> str:
    items = [
        {
            "id": item["id"],
            "channel": item["channel"],
            "title": item["title"],
            "summary": item.get("displaySummary") or _short_text(item.get("summary"), 120),
            "source": item["sourceName"],
            "url": item["url"],
        }
        for item in materials
    ]
    return f"""
请根据这些素材生成双频道简报 JSON。

社会热点频道关注：事件、趋势、争议、现实冲突、风险和可观察的时代变化。
故事素材频道关注：人物原型、地点场景、冲突机制、时代细节、奇观设定、一句话脑洞。

输入素材：
{json.dumps(items, ensure_ascii=False)}

输出结构：
{{
  "headline": "一句话总标题",
  "sections": [
    {{
      "channel": "social",
      "items": [
        {{
          "materialId": 1,
          "translatedTitle": "如果原文标题不是中文，给出中文译名；如果原文是中文，也给出润色后的中文标题",
          "category": "现实冲突",
          "summary": "不超过80字的中文摘要",
          "reason": "为什么值得看",
          "fictionFit": "高/中/低，判断这条素材是否适合作为小说素材",
          "fictionAngle": "如果适合，给出一个可转化成小说的冲突、人物或场景角度；如果不适合，说明原因",
          "keywords": ["关键词"]
        }}
      ]
    }},
    {{
      "channel": "story",
      "items": []
    }}
  ]
}}

硬性要求：
- headline、translatedTitle、category、summary、reason、keywords 必须全部是中文。
- 每条素材都必须给 fictionFit 和 fictionAngle；社会热点也要判断是否能转化为小说素材。
- 如果素材标题或摘要是英文，请不要原样复制到 summary/reason，而要翻译、压缩并解释它对中文写作者的价值。
- 保留 materialId 以便系统链接回原始素材；不要改写原文 URL。
""".strip()


async def generate_brief_for_date(date: str, cfg, app_base_url: str = "http://localhost:3000", force: bool = False) -> dict:
    existing = get_brief_by_date(date)
    if existing and not force:
        return existing
    materials = _materials_for_brief(date)
    if not materials:
        brief = {
            "headline": "今日暂无新素材",
            "sections": [
                {"channel": CHANNEL_SOCIAL, "items": []},
                {"channel": CHANNEL_STORY, "items": []},
            ],
        }
    else:
        provider = get_text_provider(cfg.text)
        raw = await provider.chat(_brief_system_prompt(), _brief_user_prompt(materials))
        brief = parse_json_loose(raw)
        _apply_brief_annotations(brief)
    html_body = render_brief_html(date, brief, app_base_url)
    text_body = render_brief_text(date, brief)
    subject = f"AI 编辑部每日简报 {date}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO brief_runs (date, status, subject, html, text, error, created_at, sent_at)
            VALUES (?, 'draft', ?, ?, ?, NULL, ?, NULL)
            ON CONFLICT(date) DO UPDATE SET
              status = 'draft',
              subject = excluded.subject,
              html = excluded.html,
              text = excluded.text,
              error = NULL,
              created_at = excluded.created_at,
              sent_at = NULL
            """,
            (date, subject, html_body, text_body, _now()),
        )
        row = conn.execute("SELECT * FROM brief_runs WHERE date = ?", (date,)).fetchone()
    return brief_row_to_dict(row)


def _apply_brief_annotations(brief: dict) -> None:
    with connect() as conn:
        for section in brief.get("sections", []):
            for item in section.get("items", []):
                material_id = item.get("materialId") or item.get("material_id")
                if not material_id:
                    continue
                conn.execute(
                    """
                    UPDATE materials
                    SET ai_category = ?, ai_summary = ?, ai_reason = ?, keywords = ?, fiction_fit = ?, fiction_angle = ?
                    WHERE id = ?
                    """,
                    (
                        (item.get("category") or "").strip(),
                        (item.get("summary") or "").strip(),
                        (item.get("reason") or "").strip(),
                        json.dumps(item.get("keywords") or [], ensure_ascii=False),
                        (item.get("fictionFit") or item.get("fiction_fit") or "").strip(),
                        (item.get("fictionAngle") or item.get("fiction_angle") or "").strip(),
                        material_id,
                    ),
                )


def _material_by_id_map() -> dict[int, dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT m.*, s.name AS source_name
            FROM materials m
            INNER JOIN rss_sources s ON s.id = m.source_id
            """
        ).fetchall()
    return {row["id"]: material_row_to_dict(row) for row in rows}


def render_brief_html(date: str, brief: dict, app_base_url: str) -> str:
    materials = _material_by_id_map()
    sections = []
    for channel in (CHANNEL_SOCIAL, CHANNEL_STORY):
        section = next((item for item in brief.get("sections", []) if item.get("channel") == channel), None) or {}
        cards = []
        for item in section.get("items", []):
            material_id = item.get("materialId") or item.get("material_id")
            material = materials.get(int(material_id)) if material_id else None
            if not material:
                continue
            display_title = item.get("translatedTitle") or item.get("translated_title") or material["title"]
            fiction_fit = item.get("fictionFit") or item.get("fiction_fit") or material.get("fictionFit") or ""
            fiction_angle = item.get("fictionAngle") or item.get("fiction_angle") or material.get("fictionAngle") or ""
            fiction_block = ""
            if fiction_fit or fiction_angle:
                fiction_block = (
                    f'<p class="fiction-fit"><strong>小说素材适配度：{html.escape(fiction_fit or "未判断")}</strong>'
                    f'{(" · " + html.escape(fiction_angle)) if fiction_angle else ""}</p>'
                )
            keywords = " ".join(f"<span>{html.escape(str(k))}</span>" for k in (item.get("keywords") or []))
            detail_url = f"{app_base_url.rstrip('/')}/#/materials/{material['id']}"
            cards.append(
                f"""
                <article class="item">
                  <h3>{html.escape(display_title)}</h3>
                  <p class="meta">原题：{html.escape(material["title"])}</p>
                  <p class="meta">{html.escape(material.get("sourceName") or "")} · {html.escape(item.get("category") or "")}</p>
                  <p>{html.escape(item.get("summary") or material.get("displaySummary") or "")}</p>
                  <p class="reason">{html.escape(item.get("reason") or "")}</p>
                  {fiction_block}
                  <p class="keywords">{keywords}</p>
                  <p><a href="{html.escape(detail_url)}">在应用中深读</a> · <a href="{html.escape(material["url"])}">查看原文</a></p>
                </article>
                """
            )
        if not cards:
            cards.append("<p class=\"empty\">今天这个频道暂时没有新素材。</p>")
        sections.append(f"<section><h2>{CHANNEL_LABELS[channel]}</h2>{''.join(cards)}</section>")
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #202124; line-height: 1.65; }}
.wrap {{ max-width: 760px; margin: 0 auto; padding: 24px; }}
h1 {{ font-size: 24px; }}
h2 {{ border-top: 1px solid #ddd; padding-top: 24px; }}
.item {{ padding: 14px 0; border-bottom: 1px solid #eee; }}
.meta, .reason, .empty {{ color: #666; }}
.fiction-fit {{ background: #fff7ed; border-left: 3px solid #f97316; padding: 8px 10px; }}
.keywords span {{ display: inline-block; background: #f1f3f4; border-radius: 999px; padding: 2px 8px; margin-right: 6px; }}
a {{ color: #0b57d0; }}
</style></head><body><div class="wrap">
<h1>{html.escape(brief.get("headline") or "AI 编辑部每日简报")}</h1>
<p class="meta">{html.escape(date)}</p>
{''.join(sections)}
</div></body></html>"""


def render_brief_text(date: str, brief: dict) -> str:
    lines = [brief.get("headline") or "AI 编辑部每日简报", date, ""]
    for section in brief.get("sections", []):
        lines.append(CHANNEL_LABELS.get(section.get("channel"), section.get("channel", "")))
        for item in section.get("items", []):
            lines.append(f"- {item.get('summary') or ''} ({item.get('category') or ''})")
        lines.append("")
    return "\n".join(lines)


def get_brief_by_date(date: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM brief_runs WHERE date = ?", (date,)).fetchone()
    return brief_row_to_dict(row) if row else None


def list_briefs(limit: int = 30) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM brief_runs ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
    return [brief_row_to_dict(row) for row in rows]


def brief_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "date": row["date"],
        "status": row["status"],
        "subject": row["subject"],
        "html": row["html"],
        "text": row["text"],
        "error": row["error"],
        "createdAt": row["created_at"],
        "sentAt": row["sent_at"],
    }


def _material_prompt(material: dict, mode: str) -> tuple[str, str]:
    base = {
        "title": material["title"],
        "summary": material["summary"],
        "source": material["sourceName"],
        "url": material["url"],
        "channel": material["channel"],
    }
    if mode == "deep":
        return (
            "你是小说素材编辑，请基于用户保存的 RSS 素材做深读拆解，只输出 JSON。"
            "无论素材原文是什么语言，输出内容必须全部使用自然中文；英文标题和摘要要先翻译理解再分析。",
            f"""
素材：
{json.dumps(base, ensure_ascii=False)}

输出 JSON：
{{
  "translatedTitle": "中文译名或润色后的中文标题",
  "background": "背景脉络",
  "conflict": "可见冲突",
  "questions": ["值得追问的问题"],
  "angles": ["可写作角度"]
}}
""".strip(),
        )
    return (
        "你是小说创意编辑，请把素材转成可写作灵感，只输出 JSON。"
        "无论素材原文是什么语言，输出内容必须全部使用自然中文；英文标题和摘要要先翻译理解再转化。",
        f"""
素材：
{json.dumps(base, ensure_ascii=False)}

输出 JSON：
{{
  "translatedTitle": "中文译名或润色后的中文标题",
  "premises": ["3-5个小说 premise"],
  "characters": ["人物设定"],
  "scenes": ["场景练习"]
}}
""".strip(),
    )


async def generate_deep_dive(material_id: int, cfg) -> dict:
    material = get_material(material_id)
    if not material:
        raise ValueError("material not found")
    system, user = _material_prompt(material, "deep")
    raw = await get_text_provider(cfg.text).chat(system, user)
    data = parse_json_loose(raw)
    with connect() as conn:
        conn.execute("UPDATE materials SET deep_dive = ? WHERE id = ?", (json.dumps(data, ensure_ascii=False), material_id))
    return data


async def generate_story_ideas(material_id: int, cfg) -> dict:
    material = get_material(material_id)
    if not material:
        raise ValueError("material not found")
    system, user = _material_prompt(material, "ideas")
    raw = await get_text_provider(cfg.text).chat(system, user)
    data = parse_json_loose(raw)
    with connect() as conn:
        conn.execute("UPDATE materials SET story_ideas = ? WHERE id = ?", (json.dumps(data, ensure_ascii=False), material_id))
    return data


def load_smtp_config(mask_secret: bool = False) -> dict:
    raw = get_config("editorial_smtp") or {}
    password = raw.get("password", "")
    if password and is_encrypted(password):
        password_plain = decrypt_secret(password)
    else:
        password_plain = password
    result = {
        "host": raw.get("host", ""),
        "port": int(raw.get("port") or 465),
        "username": raw.get("username", ""),
        "password": MASK if mask_secret and password_plain else password_plain,
        "fromEmail": raw.get("fromEmail", ""),
        "toEmail": raw.get("toEmail", ""),
        "useTls": bool(raw.get("useTls", True)),
        "configured": bool(raw.get("host") and raw.get("username") and password_plain and raw.get("toEmail")),
    }
    return result


def create_or_update_smtp_config(payload: dict) -> dict:
    current = load_smtp_config(mask_secret=False)
    password = payload.get("password", "")
    if password in ("", MASK):
        password = current.get("password", "")
    value = {
        "host": (payload.get("host") or "").strip(),
        "port": int(payload.get("port") or 465),
        "username": (payload.get("username") or "").strip(),
        "password": encrypt_secret(password) if password else "",
        "fromEmail": (payload.get("fromEmail") or payload.get("username") or "").strip(),
        "toEmail": (payload.get("toEmail") or "").strip(),
        "useTls": bool(payload.get("useTls", True)),
    }
    set_config("editorial_smtp", value)
    return load_smtp_config(mask_secret=True)


def send_brief_email(brief_id: int) -> dict:
    smtp_cfg = load_smtp_config(mask_secret=False)
    if not smtp_cfg["configured"]:
        raise ValueError("SMTP is not configured")
    with connect() as conn:
        row = conn.execute("SELECT * FROM brief_runs WHERE id = ?", (brief_id,)).fetchone()
    if not row:
        raise ValueError("brief not found")
    brief = brief_row_to_dict(row)
    msg = EmailMessage()
    msg["Subject"] = brief["subject"]
    msg["From"] = smtp_cfg["fromEmail"] or smtp_cfg["username"]
    msg["To"] = smtp_cfg["toEmail"]
    msg.set_content(brief["text"] or "")
    msg.add_alternative(brief["html"], subtype="html")
    try:
        if smtp_cfg["useTls"]:
            server = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"], timeout=20)
        else:
            server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=20)
        with server:
            if not smtp_cfg["useTls"]:
                server.starttls()
            server.login(smtp_cfg["username"], smtp_cfg["password"])
            server.send_message(msg)
        with connect() as conn:
            conn.execute(
                "UPDATE brief_runs SET status = 'sent', sent_at = ?, error = NULL WHERE id = ?",
                (_now(), brief_id),
            )
    except Exception as exc:
        with connect() as conn:
            conn.execute(
                "UPDATE brief_runs SET status = 'send_failed', error = ? WHERE id = ?",
                (str(exc), brief_id),
            )
        raise
    with connect() as conn:
        return brief_row_to_dict(conn.execute("SELECT * FROM brief_runs WHERE id = ?", (brief_id,)).fetchone())


def test_smtp_connection() -> dict:
    smtp_cfg = load_smtp_config(mask_secret=False)
    if not smtp_cfg["configured"]:
        raise ValueError("SMTP is not configured")
    host = urlparse(f"//{smtp_cfg['host']}").hostname or smtp_cfg["host"]
    if smtp_cfg["useTls"]:
        server = smtplib.SMTP_SSL(host, smtp_cfg["port"], timeout=20)
    else:
        server = smtplib.SMTP(host, smtp_cfg["port"], timeout=20)
    with server:
        if not smtp_cfg["useTls"]:
            server.starttls()
        server.login(smtp_cfg["username"], smtp_cfg["password"])
    return {"ok": True}


def load_schedule_config() -> dict:
    raw = get_config("editorial_schedule") or {}
    return {
        "sendTime": raw.get("sendTime", "08:00"),
        "autoSend": bool(raw.get("autoSend", True)),
    }


def save_schedule_config(payload: dict) -> dict:
    send_time = (payload.get("sendTime") or "08:00").strip()
    if not re.match(r"^\d{2}:\d{2}$", send_time):
        raise ValueError("sendTime must be HH:MM")
    value = {"sendTime": send_time, "autoSend": bool(payload.get("autoSend", True))}
    set_config("editorial_schedule", value)
    return value


async def run_due_editorial_job(cfg, app_base_url: str = "http://localhost:3000") -> dict:
    schedule = load_schedule_config()
    if not schedule["autoSend"]:
        return {"ran": False, "reason": "auto send disabled"}
    today = datetime.now().strftime("%Y-%m-%d")
    if datetime.now().strftime("%H:%M") < schedule["sendTime"]:
        return {"ran": False, "reason": "not due"}
    brief = get_brief_by_date(today)
    if not brief:
        await fetch_enabled_sources()
        brief = await generate_brief_for_date(today, cfg, app_base_url=app_base_url)
    if brief["status"] != "sent" and load_smtp_config(mask_secret=False)["configured"]:
        try:
            brief = send_brief_email(brief["id"])
        except Exception as exc:
            log.warning("daily editorial email failed: %s", exc)
    return {"ran": True, "brief": brief}


def start_editorial_scheduler(cfg_loader, app_base_url: str) -> None:
    def _loop() -> None:
        while True:
            try:
                cfg = cfg_loader()
                import asyncio

                asyncio.run(run_due_editorial_job(cfg, app_base_url=app_base_url))
            except Exception as exc:
                log.info("editorial scheduler skipped: %s", exc)
            time.sleep(300)

    threading.Thread(target=_loop, daemon=True).start()
