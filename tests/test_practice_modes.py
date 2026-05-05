import os
import tempfile
import unittest
from datetime import datetime
from inspect import signature
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from my_writing import db, prompts, services
from my_writing.db import connect, init_db
from my_writing.models import FullConfig, ProviderConfig
from my_writing.providers import openai_provider
from my_writing.routers import submissions as submissions_router


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

    def test_daily_prompt_targets_story_seed_expansion(self):
        user_prompt = prompts.daily_assignment_user("场景描写")

        self.assertIn("故事种子", user_prompt)
        self.assertIn("300~800", user_prompt)
        self.assertIn("20~60", user_prompt)
        self.assertIn("环境、动作、心理", user_prompt)
        self.assertIn('"scenario"', user_prompt)

    def test_outline_prompt_targets_structure_and_conflict(self):
        user_prompt = prompts.outline_practice_user("叙事结构")

        self.assertIn("20~80", user_prompt)
        self.assertIn("100~200 字故事小纲", user_prompt)
        self.assertIn("不要写成完整故事小纲", user_prompt)
        self.assertIn("不要替学员设计冲突升级", user_prompt)
        self.assertIn("故事结构", user_prompt)
        self.assertIn("冲突", user_prompt)
        self.assertIn('"scenario"', user_prompt)

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

    async def test_outline_practice_generates_when_due_and_reuses_today_assignment(self):
        creator = getattr(services, "get_or_create_today_outline_practice", None)
        self.assertIsNotNone(creator)
        if creator is None:
            return

        with patch.object(
            services,
            "generate_outline_practice_assignment",
            AsyncMock(
                return_value={
                    "type": "outline_practice",
                    "title": "outline title",
                    "scenario": "主角终于得到机会，却发现必须背叛最信任自己的人。",
                    "image_data": None,
                    "focus_dimension": "叙事结构",
                }
            ),
        ) as gen:
            first = await creator(self.cfg)
            second = await creator(self.cfg)

        self.assertEqual(first["type"], "outline_practice")
        self.assertEqual(first["id"], second["id"])
        self.assertTrue(first["due"])
        self.assertEqual(gen.await_count, 1)

    async def test_outline_practice_waits_until_three_days_after_completion(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "outline_practice", "done outline", "outline body", None, None, f"{today}T00:00:00"),
            )
            outline_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (outline_id, today, "x" * 120, 120, "{}", "{}", f"{today}T00:01:00"),
            )

        with patch.object(services, "generate_outline_practice_assignment", AsyncMock()) as gen:
            result = await services.get_or_create_today_outline_practice(self.cfg)

        self.assertEqual(result["id"], outline_id)
        self.assertFalse(result["due"])
        self.assertEqual(result["daysUntilDue"], 3)
        self.assertEqual(gen.await_count, 0)

    def test_outline_practice_status_is_due_after_three_days(self):
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("2026-04-29", "outline_practice", "old outline", "outline body", None, None, "2026-04-29T00:00:00"),
            )
            outline_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (outline_id, "2026-04-29", "x" * 120, 120, "{}", "{}", "2026-04-29T00:01:00"),
            )

        status = services.outline_practice_status(today=datetime.strptime("2026-05-02", "%Y-%m-%d").date())

        self.assertTrue(status["due"])
        self.assertEqual(status["nextAvailableDate"], "2026-05-02")

    def test_submission_minimums_by_assignment_type(self):
        self.assertEqual(submissions_router.min_char_count_for_assignment_type("daily"), 300)
        self.assertEqual(submissions_router.min_char_count_for_assignment_type("outline_practice"), 100)
        self.assertEqual(submissions_router.min_char_count_for_assignment_type("image_practice"), 500)
        self.assertEqual(submissions_router.min_char_count_for_assignment_type("journal"), 1)

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
