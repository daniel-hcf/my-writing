import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from my_writing import db
from my_writing.db import connect, init_db
from my_writing.editorial import (
    CHANNEL_SOCIAL,
    CHANNEL_STORY,
    create_or_update_smtp_config,
    create_source,
    generate_brief_for_date,
    generate_deep_dive,
    generate_story_ideas,
    get_material,
    import_source_pack,
    list_source_packs,
    load_smtp_config,
    parse_feed_xml,
    send_brief_email,
    upsert_material,
)
from my_writing.models import FullConfig, ProviderConfig


def make_cfg() -> FullConfig:
    return FullConfig(
        text=ProviderConfig(provider="openai", apiKey="sk-text", baseUrl="https://example.com", model="gpt-4o"),
        image=ProviderConfig(provider="openai", apiKey="sk-image", baseUrl="https://example.com", model="gpt-image-1"),
    )


class EditorialTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "data.db")
        self.key = Fernet.generate_key().decode()
        self.env = patch.dict(os.environ, {"MY_WRITING_ENCRYPTION_KEY": self.key}, clear=False)
        self.env.start()
        self.db_patch = patch.object(db, "DB_PATH", self.db_path)
        self.db_patch.start()
        init_db()

    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 10

    def tearDown(self):
        self.db_patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_source_pack_import_skips_existing_urls(self):
        packs = list_source_packs()
        self.assertIn("story", {pack["id"] for pack in packs})

        first = import_source_pack("story")
        second = import_source_pack("story")

        self.assertGreater(first["imported"], 0)
        self.assertEqual(second["imported"], 0)
        self.assertGreaterEqual(second["skipped"], first["imported"])

        with connect() as conn:
            urls = [row["url"] for row in conn.execute("SELECT url FROM rss_sources").fetchall()]
        self.assertEqual(len(urls), len(set(urls)))

    def test_source_packs_recommend_github_hot_search_chinanews_and_reddit(self):
        social_pack = next(pack for pack in list_source_packs() if pack["id"] == "social")
        story_pack = next(pack for pack in list_source_packs() if pack["id"] == "story")
        urls = [source["url"] for pack in (social_pack, story_pack) for source in pack["sources"]]

        self.assertIn("https://rsshub.app/github/trending/daily/any/any", urls)
        self.assertIn("https://rsshub.app/weibo/search/hot/fulltext", urls)
        self.assertIn("https://rsshub.app/baidu/top", urls)
        self.assertIn("https://www.reddit.com/r/nosleep/.rss", urls)
        self.assertIn("https://www.reddit.com/r/UnresolvedMysteries/.rss", urls)
        self.assertIn("https://www.chinanews.com.cn/rss/world.xml", urls)
        self.assertIn("https://www.chinanews.com.cn/rss/society.xml", urls)
        for pack in (social_pack, story_pack):
            for source in pack["sources"]:
                self.assertNotIn("?", source["name"])

        removed = [
            "https://36kr.com/feed-article",
            "https://36kr.com/feed-newsflash",
            "https://daily.jstor.org/feed/",
            "https://publicdomainreview.org/rss.xml",
            "https://aeon.co/feed.rss",
            "https://rsshub.app/sspai/index",
            "https://rsshub.app/v2ex/topics/hot",
        ]
        for url in removed:
            self.assertNotIn(url, urls)

    def test_material_schema_tracks_fiction_suitability(self):
        source = create_source("V2EX 热门", "https://example.com/v2ex.xml", CHANNEL_SOCIAL)
        material_id = upsert_material(
            source["id"],
            CHANNEL_SOCIAL,
            {
                "title": "有人在 V2EX 讨论一座无人便利店",
                "summary": "技术社区里的日常议题可能有故事张力。",
                "url": "https://example.com/v2ex-store",
            },
        )
        with connect() as conn:
            conn.execute(
                """
                UPDATE materials
                SET fiction_fit = ?, fiction_angle = ?
                WHERE id = ?
                """,
                ("高", "无人便利店适合写成孤独城市里的夜间相遇。", material_id),
            )

        item = get_material(material_id)
        self.assertEqual(item["fictionFit"], "高")
        self.assertIn("夜间相遇", item["fictionAngle"])

    def test_deleting_source_removes_its_materials_from_library_and_brief_pool(self):
        source = create_source("36氪文章", "https://36kr.com/feed-article", CHANNEL_SOCIAL)
        material_id = upsert_material(
            source["id"],
            CHANNEL_SOCIAL,
            {
                "title": "不想再看的商业稿",
                "summary": "删除源后，这条素材不应继续出现。",
                "url": "https://36kr.com/p/not-wanted?f=rss",
            },
        )

        from my_writing.editorial import _materials_for_brief, delete_source, list_materials

        delete_source(source["id"])

        self.assertFalse(any(item["id"] == material_id for item in list_materials(limit=20)))
        self.assertFalse(any(item["id"] == material_id for item in _materials_for_brief("2026-05-06")))

    def test_parse_feed_xml_reads_rss_and_atom_entries(self):
        rss = """
        <rss><channel>
          <item>
            <title>Hidden library reopens</title>
            <link>https://example.com/library</link>
            <description><![CDATA[<p>A city finds old letters.</p>]]></description>
            <pubDate>Wed, 06 May 2026 08:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """
        atom = """
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>River town ritual</title>
            <link href="https://example.com/ritual" />
            <summary>A ritual returns after fifty years.</summary>
            <updated>2026-05-06T09:00:00Z</updated>
          </entry>
        </feed>
        """

        self.assertEqual(parse_feed_xml(rss)[0]["summary"], "A city finds old letters.")
        self.assertEqual(parse_feed_xml(atom)[0]["url"], "https://example.com/ritual")

    def test_material_list_exposes_short_display_summary(self):
        source = create_source("Reddit NoSleep", "https://example.com/reddit.xml", CHANNEL_STORY)
        long_summary = "This is a very long Reddit post excerpt. " * 30
        material_id = upsert_material(
            source["id"],
            CHANNEL_STORY,
            {"title": "Long post", "summary": long_summary, "url": "https://example.com/long"},
        )

        item = get_material(material_id)

        self.assertLessEqual(len(item["displaySummary"]), 123)
        self.assertTrue(item["displaySummary"].endswith("..."))
        self.assertEqual(item["summary"], long_summary.strip())

    async def test_brief_prompt_uses_short_summary_for_long_reddit_posts(self):
        source = create_source("Reddit NoSleep", "https://example.com/reddit.xml", CHANNEL_STORY)
        upsert_material(
            source["id"],
            CHANNEL_STORY,
            {
                "title": "Long post",
                "summary": "Reddit正文 " * 200,
                "url": "https://example.com/long-reddit",
            },
        )

        with patch("my_writing.editorial.get_text_provider") as provider_factory:
            provider = provider_factory.return_value
            provider.chat = AsyncMock(
                return_value=json.dumps(
                    {
                        "headline": "短摘要测试",
                        "sections": [{"channel": CHANNEL_SOCIAL, "items": []}, {"channel": CHANNEL_STORY, "items": []}],
                    },
                    ensure_ascii=False,
                )
            )
            await generate_brief_for_date("2026-05-06", make_cfg(), force=True)

        prompt = provider.chat.await_args.args[1]
        self.assertLess(len(prompt), 2500)
        self.assertIn("...", prompt)

    def test_brief_prompt_requires_chinese_translation_for_english_sources(self):
        from my_writing.editorial import _brief_system_prompt, _brief_user_prompt, _material_prompt

        material = {
            "id": 1,
            "channel": CHANNEL_STORY,
            "title": "A vanished island map is found",
            "summary": "Archivists discover a town that never existed.",
            "sourceName": "Atlas Obscura",
            "url": "https://example.com/island",
        }

        prompt = _brief_system_prompt() + "\n" + _brief_user_prompt([material])
        self.assertIn("中文", prompt)
        self.assertIn("翻译", prompt)
        self.assertIn("translatedTitle", prompt)

        deep_system, deep_user = _material_prompt(material, "deep")
        ideas_system, ideas_user = _material_prompt(material, "ideas")
        self.assertIn("中文", deep_system + deep_user)
        self.assertIn("中文", ideas_system + ideas_user)

    async def test_generate_brief_classifies_two_channels_and_saves_email_html(self):
        social_source = create_source("Reuters Tech", "https://example.com/social.xml", CHANNEL_SOCIAL)
        story_source = create_source("Atlas Obscura", "https://example.com/story.xml", CHANNEL_STORY)
        social_id = upsert_material(
            social_source["id"],
            CHANNEL_SOCIAL,
            {
                "title": "Cities regulate delivery robots",
                "summary": "New rules reveal labor and street conflicts.",
                "url": "https://example.com/robots",
                "published_at": "2026-05-06T08:00:00Z",
            },
        )
        story_id = upsert_material(
            story_source["id"],
            CHANNEL_STORY,
            {
                "title": "A vanished island map is found",
                "summary": "Archivists discover a map with a town that never existed.",
                "url": "https://example.com/island",
                "published_at": "2026-05-06T08:00:00Z",
            },
        )
        payload = {
            "headline": "Today's editorial radar",
            "sections": [
                {
                    "channel": CHANNEL_SOCIAL,
                    "items": [
                        {
                            "materialId": social_id,
                            "translatedTitle": "城市开始监管配送机器人",
                            "category": "现实冲突",
                            "summary": "机器人进入街道治理议题。",
                            "reason": "能观察技术、劳动和公共空间的冲突。",
                            "fictionFit": "中",
                            "fictionAngle": "可以写一个失业骑手和配送机器人共享夜路的故事。",
                            "keywords": ["机器人", "城市"],
                        }
                    ],
                },
                {
                    "channel": CHANNEL_STORY,
                    "items": [
                        {
                            "materialId": story_id,
                            "translatedTitle": "一张消失岛屿的地图被发现",
                            "category": "奇观设定",
                            "summary": "不存在的小镇地图适合悬疑开场。",
                            "reason": "具备失踪地点和档案谜团。",
                            "fictionFit": "高",
                            "fictionAngle": "适合写成档案馆员追查一座不存在小镇的悬疑线。",
                            "keywords": ["地图", "岛"],
                        }
                    ],
                },
            ],
        }

        with patch("my_writing.editorial.get_text_provider") as provider_factory:
            provider = provider_factory.return_value
            provider.chat = AsyncMock(return_value=json.dumps(payload, ensure_ascii=False))
            brief = await generate_brief_for_date("2026-05-06", make_cfg(), app_base_url="http://localhost:3000")

        self.assertEqual(brief["status"], "draft")
        self.assertIn("当前社会热点", brief["html"])
        self.assertIn("故事素材雷达", brief["html"])
        self.assertIn("小说素材适配度", brief["html"])
        self.assertIn("失业骑手", brief["html"])
        self.assertIn("/#/materials/", brief["html"])
        with connect() as conn:
            rows = conn.execute("SELECT ai_category, ai_summary, fiction_fit, fiction_angle FROM materials ORDER BY id").fetchall()
        self.assertEqual(rows[0]["ai_category"], "现实冲突")
        self.assertEqual(rows[1]["ai_category"], "奇观设定")
        self.assertEqual(rows[0]["fiction_fit"], "中")
        self.assertIn("档案馆员", rows[1]["fiction_angle"])

    async def test_force_generate_brief_replaces_existing_empty_brief(self):
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO brief_runs (date, status, subject, html, text, created_at)
                VALUES (?, 'sent', ?, ?, ?, ?)
                """,
                ("2026-05-06", "AI 编辑部每日简报 2026-05-06", "<p>空</p>", "空", "2026-05-06T08:00:00"),
            )
        source = create_source("36氪快讯", "https://example.com/social.xml", CHANNEL_SOCIAL)
        material_id = upsert_material(
            source["id"],
            CHANNEL_SOCIAL,
            {
                "title": "新的城市议题",
                "summary": "一条后来才抓到的素材。",
                "url": "https://example.com/new-topic",
                "published_at": "2026-05-06T10:00:00Z",
            },
        )
        payload = {
            "headline": "重新生成后的简报",
            "sections": [
                {
                    "channel": CHANNEL_SOCIAL,
                    "items": [
                        {
                            "materialId": material_id,
                            "category": "现实冲突",
                            "summary": "后来抓到的素材进入简报。",
                            "reason": "避免旧空简报卡住当天。",
                            "keywords": ["城市"],
                        }
                    ],
                },
                {"channel": CHANNEL_STORY, "items": []},
            ],
        }

        with patch("my_writing.editorial.get_text_provider") as provider_factory:
            provider = provider_factory.return_value
            provider.chat = AsyncMock(return_value=json.dumps(payload, ensure_ascii=False))
            brief = await generate_brief_for_date(
                "2026-05-06",
                make_cfg(),
                app_base_url="http://localhost:3000",
                force=True,
            )

        self.assertEqual(brief["status"], "draft")
        self.assertIn("后来抓到的素材进入简报", brief["html"])
        self.assertIsNone(brief["sentAt"])
        with connect() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) c FROM brief_runs").fetchone()["c"], 1)

    async def test_force_generate_updates_existing_brief_timestamp_and_resets_sent_status(self):
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO brief_runs (date, status, subject, html, text, created_at, sent_at)
                VALUES (?, 'sent', ?, ?, ?, ?, ?)
                """,
                (
                    "2026-05-06",
                    "AI 编辑部每日简报 2026-05-06",
                    "<p>old</p>",
                    "old",
                    "2026-05-06T08:00:00",
                    "2026-05-06T08:01:00",
                ),
            )
        source = create_source("GitHub Trending", "https://example.com/github.xml", CHANNEL_SOCIAL)
        material_id = upsert_material(
            source["id"],
            CHANNEL_SOCIAL,
            {"title": "新的热点", "summary": "重新抓取后的素材。", "url": "https://example.com/new"},
        )
        payload = {
            "headline": "新简报",
            "sections": [
                {
                    "channel": CHANNEL_SOCIAL,
                    "items": [
                        {
                            "materialId": material_id,
                            "translatedTitle": "新的热点",
                            "category": "技术风向",
                            "summary": "重新抓取后的素材进入简报。",
                            "reason": "证明重新生成会覆盖旧内容。",
                            "fictionFit": "中",
                            "fictionAngle": "可做技术时代背景。",
                            "keywords": ["热点"],
                        }
                    ],
                },
                {"channel": CHANNEL_STORY, "items": []},
            ],
        }

        with patch("my_writing.editorial.get_text_provider") as provider_factory:
            provider = provider_factory.return_value
            provider.chat = AsyncMock(return_value=json.dumps(payload, ensure_ascii=False))
            brief = await generate_brief_for_date("2026-05-06", make_cfg(), force=True)

        self.assertEqual(brief["status"], "draft")
        self.assertIsNone(brief["sentAt"])
        self.assertNotEqual(brief["createdAt"], "2026-05-06T08:00:00")
        self.assertIn("重新抓取后的素材进入简报", brief["html"])

    async def test_generate_brief_uses_materials_collected_today_even_if_published_earlier(self):
        source = create_source("Public Domain Review", "https://example.com/story.xml", CHANNEL_STORY)
        material_id = upsert_material(
            source["id"],
            CHANNEL_STORY,
            {
                "title": "百年前的海边仪式",
                "summary": "RSS 中的旧文章今天才被收集进素材库。",
                "url": "https://example.com/old-ritual",
                "published_at": "2024-01-01T00:00:00Z",
            },
        )
        payload = {
            "headline": "故事素材雷达",
            "sections": [
                {"channel": CHANNEL_SOCIAL, "items": []},
                {
                    "channel": CHANNEL_STORY,
                    "items": [
                        {
                            "materialId": material_id,
                            "category": "时代细节",
                            "summary": "旧文章也能成为今天收集到的小说素材。",
                            "reason": "故事素材不应只看原文发布日期。",
                            "keywords": ["仪式"],
                        }
                    ],
                },
            ],
        }

        with patch("my_writing.editorial.get_text_provider") as provider_factory:
            provider = provider_factory.return_value
            provider.chat = AsyncMock(return_value=json.dumps(payload, ensure_ascii=False))
            brief = await generate_brief_for_date("2026-05-06", make_cfg(), force=True)

        prompt = provider.chat.await_args.args[1]
        self.assertIn("百年前的海边仪式", prompt)
        self.assertIn("旧文章也能成为今天收集到的小说素材", brief["html"])

    async def test_deep_dive_and_story_ideas_are_saved_on_material(self):
        source = create_source("Story Feed", "https://example.com/story.xml", CHANNEL_STORY)
        material_id = upsert_material(
            source["id"],
            CHANNEL_STORY,
            {"title": "Old train station", "summary": "A sealed room is found.", "url": "https://example.com/train"},
        )

        with patch("my_writing.editorial.get_text_provider") as provider_factory:
            provider = provider_factory.return_value
            provider.chat = AsyncMock(
                side_effect=[
                    json.dumps({"background": "背景", "conflict": "冲突", "questions": ["为什么"], "angles": ["角度"]}, ensure_ascii=False),
                    json.dumps({"premises": ["灵感1"], "characters": ["人物1"], "scenes": ["场景1"]}, ensure_ascii=False),
                ]
            )
            deep = await generate_deep_dive(material_id, make_cfg())
            ideas = await generate_story_ideas(material_id, make_cfg())

        self.assertEqual(deep["background"], "背景")
        self.assertEqual(ideas["premises"], ["灵感1"])

    def test_smtp_config_encrypts_secret_and_masks_loaded_value(self):
        create_or_update_smtp_config(
            {
                "host": "smtp.example.com",
                "port": 465,
                "username": "me@example.com",
                "password": "mail-secret",
                "fromEmail": "me@example.com",
                "toEmail": "reader@example.com",
                "useTls": True,
            }
        )

        with connect() as conn:
            raw = conn.execute("SELECT value FROM config WHERE key = 'editorial_smtp'").fetchone()["value"]
        self.assertNotIn("mail-secret", raw)

        cfg = load_smtp_config(mask_secret=True)
        self.assertEqual(cfg["password"], "***")
        self.assertTrue(cfg["configured"])

    def test_sent_brief_can_be_sent_again(self):
        create_or_update_smtp_config(
            {
                "host": "smtp.example.com",
                "port": 465,
                "username": "me@example.com",
                "password": "mail-secret",
                "fromEmail": "me@example.com",
                "toEmail": "reader@example.com",
                "useTls": True,
            }
        )
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO brief_runs (date, status, subject, html, text, created_at, sent_at)
                VALUES (?, 'sent', ?, ?, ?, ?, ?)
                """,
                (
                    "2026-05-06",
                    "AI 编辑部每日简报 2026-05-06",
                    "<p>hello</p>",
                    "hello",
                    "2026-05-06T08:00:00",
                    "2026-05-06T08:01:00",
                ),
            )

        class FakeSMTP:
            sent = 0

            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def login(self, *_args):
                pass

            def send_message(self, _msg):
                FakeSMTP.sent += 1

        with patch("my_writing.editorial.smtplib.SMTP_SSL", FakeSMTP):
            first = send_brief_email(1)
            second = send_brief_email(1)

        self.assertEqual(FakeSMTP.sent, 2)
        self.assertEqual(first["status"], "sent")
        self.assertEqual(second["status"], "sent")
