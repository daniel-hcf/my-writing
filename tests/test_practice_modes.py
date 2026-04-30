import os
import tempfile
import unittest
from datetime import datetime
from inspect import signature
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from my_writing import db, services
from my_writing.db import connect, init_db
from my_writing.models import FullConfig, ProviderConfig
from my_writing.providers import openai_provider


def make_cfg() -> FullConfig:
    return FullConfig(
        text=ProviderConfig(provider="openai", apiKey="sk-text", baseUrl="https://example.com", model="gpt-4o"),
        image=ProviderConfig(provider="openai", apiKey="sk-image", baseUrl="https://example.com", model="gpt-image-1"),
    )


class PracticeModesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "data.db")
        self.key = Fernet.generate_key().decode()
        self.env = patch.dict(os.environ, {"MY_WRITING_ENCRYPTION_KEY": self.key}, clear=False)
        self.env.start()
        self.db_patch = patch.object(db, "DB_PATH", self.db_path)
        self.db_patch.start()
        init_db()
        self.cfg = make_cfg()

    def tearDown(self):
        self.db_patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_init_db_migrates_legacy_assignment_types(self):
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2026-04-29", "scenario", "legacy daily", "scenario body", None, None, "2026-04-29T00:00:00"),
            )
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2026-04-29", "image", "legacy image", None, "data:image/png;base64,abc", None, "2026-04-29T00:00:00"),
            )
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2026-04-29", "journal", "legacy journal", None, None, None, "2026-04-29T00:00:00"),
            )

        init_db()

        with connect() as conn:
            types = [r["type"] for r in conn.execute("SELECT type FROM assignments ORDER BY id ASC").fetchall()]

        self.assertEqual(types, ["daily", "image_practice", "journal"])

    async def test_get_or_create_today_assignment_returns_daily_and_reuses_it(self):
        generator = getattr(services, "generate_daily_assignment", None)
        self.assertIsNotNone(generator)
        if generator is None:
            return

        with patch.object(
            services,
            "generate_daily_assignment",
            AsyncMock(
                return_value={
                    "type": "daily",
                    "title": "today daily",
                    "scenario": "write from a scene",
                    "image_data": None,
                    "focus_dimension": "叙事结构",
                }
            ),
        ) as gen:
            first = await services.get_or_create_today_assignment(self.cfg)
            second = await services.get_or_create_today_assignment(self.cfg)

        self.assertEqual(first["type"], "daily")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(gen.await_count, 1)

    async def test_image_practice_reuses_current_unsubmitted_and_allows_new_after_submit(self):
        creator = getattr(services, "get_or_create_today_image_practice", None)
        self.assertIsNotNone(creator)
        if creator is None:
            return

        with patch.object(
            services,
            "generate_image_practice_assignment",
            AsyncMock(
                side_effect=[
                    {
                        "type": "image_practice",
                        "title": "first image",
                        "scenario": None,
                        "image_data": "data:image/png;base64,aaa",
                        "focus_dimension": None,
                    },
                    {
                        "type": "image_practice",
                        "title": "second image",
                        "scenario": None,
                        "image_data": "data:image/png;base64,bbb",
                        "focus_dimension": None,
                    },
                ]
            ),
        ) as gen:
            first = await creator(self.cfg)
            reused = await creator(self.cfg)

            with connect() as conn:
                conn.execute(
                    """
                    INSERT INTO submissions
                      (assignment_id, date, content, char_count, scores, feedback, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        first["id"],
                        datetime.now().strftime("%Y-%m-%d"),
                        "x" * 500,
                        500,
                        "{}",
                        "{}",
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )

            next_one = await creator(self.cfg)

        self.assertEqual(first["id"], reused["id"])
        self.assertNotEqual(first["id"], next_one["id"])
        self.assertEqual(gen.await_count, 2)

    async def test_replace_current_image_practice_replaces_unsubmitted_assignment(self):
        replacer = getattr(services, "replace_today_image_practice", None)
        creator = getattr(services, "get_or_create_today_image_practice", None)
        self.assertIsNotNone(replacer)
        self.assertIsNotNone(creator)
        if not replacer or not creator:
            return

        with patch.object(
            services,
            "generate_image_practice_assignment",
            AsyncMock(
                side_effect=[
                    {
                        "type": "image_practice",
                        "title": "old image",
                        "scenario": None,
                        "image_data": "data:image/png;base64,aaa",
                        "focus_dimension": None,
                    },
                    {
                        "type": "image_practice",
                        "title": "new image",
                        "scenario": None,
                        "image_data": "data:image/png;base64,bbb",
                        "focus_dimension": None,
                    },
                ]
            ),
        ):
            first = await creator(self.cfg)
            replaced = await replacer(self.cfg)

        self.assertNotEqual(first["id"], replaced["id"])
        with connect() as conn:
            active = conn.execute(
                """
                SELECT id, title FROM assignments
                WHERE date = ? AND type = 'image_practice'
                ORDER BY id ASC
                """,
                (datetime.now().strftime("%Y-%m-%d"),),
            ).fetchall()
        self.assertEqual([r["title"] for r in active], ["new image"])

    def test_collect_stats_supports_mode_filtering(self):
        self.assertIn("mode", signature(services.collect_stats).parameters)
        if "mode" not in signature(services.collect_stats).parameters:
            return

        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2026-04-29", "daily", "daily title", "daily body", None, None, "2026-04-29T00:00:00"),
            )
            daily_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2026-04-29", "image_practice", "image title", None, "data:image/png;base64,abc", None, "2026-04-29T00:01:00"),
            )
            image_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (daily_id, "2026-04-29", "daily text", 500, '{"人物塑造": 8}', '{"dims": {}, "overall": ""}', "2026-04-29T00:00:00"),
            )
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (image_id, "2026-04-29", "image text", 500, '{"人物塑造": 6}', '{"dims": {}, "overall": ""}', "2026-04-29T00:01:00"),
            )

        all_stats = services.collect_stats(mode="all")
        daily_stats = services.collect_stats(mode="daily")
        image_stats = services.collect_stats(mode="image_practice")

        self.assertEqual(len(all_stats["series"]), 2)
        self.assertEqual(len(daily_stats["series"]), 1)
        self.assertEqual(len(image_stats["series"]), 1)
        self.assertEqual(daily_stats["latest"]["人物塑造"], 8)
        self.assertEqual(image_stats["latest"]["人物塑造"], 6)

    def test_normalize_downloaded_image_mime_type(self):
        normalizer = getattr(openai_provider, "_normalize_image_content_type", None)
        self.assertIsNotNone(normalizer)
        if normalizer is None:
            return

        png_type = normalizer(
            "application/octet-stream",
            b"\x89PNG\r\n\x1a\nrest",
            "https://example.com/test.png",
        )
        jpeg_type = normalizer(
            "application/octet-stream",
            b"\xff\xd8\xff\xe0rest",
            "https://example.com/test.jpg",
        )

        self.assertEqual(png_type, "image/png")
        self.assertEqual(jpeg_type, "image/jpeg")


if __name__ == "__main__":
    unittest.main()
