import os
import tempfile
import unittest
from datetime import datetime
from inspect import signature
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from my_writing import config, db, prompts, services
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

    def test_init_db_creates_assignment_drafts_table(self):
        with connect() as conn:
            columns = {
                r["name"]
                for r in conn.execute("PRAGMA table_info(assignment_drafts)").fetchall()
            }

        self.assertIn("assignment_id", columns)
        self.assertIn("content", columns)
        self.assertIn("char_count", columns)
        self.assertIn("updated_at", columns)

    def test_assignment_draft_save_overwrites_existing_content(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "draft title", "draft body", None, None, f"{today}T00:00:00"),
            )
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        first = services.save_assignment_draft(aid, "first draft")
        second = services.save_assignment_draft(aid, "second draft")

        self.assertEqual(first["assignmentId"], aid)
        self.assertEqual(second["draftContent"], "second draft")
        self.assertEqual(second["draftCharCount"], len("second draft"))
        with connect() as conn:
            rows = conn.execute("SELECT content FROM assignment_drafts WHERE assignment_id = ?", (aid,)).fetchall()
        self.assertEqual([r["content"] for r in rows], ["second draft"])

    def test_assignment_draft_rejects_submitted_assignment(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "submitted", "body", None, None, f"{today}T00:00:00"),
            )
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (aid, today, "x" * 300, 300, "{}", "{}", f"{today}T00:01:00"),
            )

        with self.assertRaisesRegex(ValueError, "assignment_already_submitted"):
            services.save_assignment_draft(aid, "late draft")

    def test_daily_prompt_targets_rhythm_with_user_scene_intent(self):
        self.assertEqual(config.DIMENSIONS, ["节奏"])
        user_prompt = prompts.daily_assignment_user("节奏", intent="宗门审判")

        self.assertIn("故事种子", user_prompt)
        self.assertIn("男频爽文", user_prompt)
        self.assertIn("题材/场景", user_prompt)
        self.assertIn("宗门审判", user_prompt)
        self.assertIn("钩子", user_prompt)
        self.assertIn("压迫", user_prompt)
        self.assertIn("反击期待", user_prompt)
        self.assertIn("爽点兑现", user_prompt)
        self.assertIn("追读", user_prompt)
        self.assertIn("300~800", user_prompt)
        self.assertIn("20~60", user_prompt)
        self.assertIn('"scenario"', user_prompt)

    def test_outline_prompt_targets_structure_and_conflict(self):
        user_prompt = prompts.outline_practice_user("叙事结构")

        self.assertIn("男频爽文", user_prompt)
        self.assertIn("爽点", user_prompt)
        self.assertIn("反击", user_prompt)
        self.assertIn("升级", user_prompt)
        self.assertIn("尾钩", user_prompt)
        self.assertIn("20~80", user_prompt)
        self.assertIn("100~200 字故事小纲", user_prompt)
        self.assertIn("不要写成完整故事小纲", user_prompt)
        self.assertIn("不要替学员设计冲突升级", user_prompt)
        self.assertIn("故事结构", user_prompt)
        self.assertIn("冲突", user_prompt)
        self.assertIn('"scenario"', user_prompt)

    def test_image_prompt_targets_male_webnovel_visual_conflict(self):
        user_prompt = prompts.image_practice_user("人物塑造")

        self.assertIn("男频爽文", user_prompt)
        self.assertIn("爽点", user_prompt)
        self.assertIn("压迫", user_prompt)
        self.assertIn("资源争夺", user_prompt)
        self.assertIn("强敌逼迫", user_prompt)
        self.assertIn("追读", user_prompt)
        self.assertIn('"title"', user_prompt)
        self.assertIn('"imagePrompt"', user_prompt)

    def test_scoring_prompt_uses_strict_male_webnovel_editor_standards(self):
        system_prompt = prompts.scoring_system()
        user_prompt = prompts.scoring_user(
            {
                "type": "daily",
                "title": "宗门审判",
                "scenario": "众人逼主角交出祖传玉牌时，他听见玉牌里传来师尊的声音。",
                "focus_dimension": "节奏",
            },
            "x" * 320,
        )
        combined = system_prompt + "\n" + user_prompt

        for word in ("男频爽文", "责编", "网文节奏", "钩子", "压迫", "反击期待", "爽点兑现", "追读"):
            self.assertIn(word, combined)
        for field in ("rhythm_score", "market_score", "training_score", "fatal_problem", "best_part", "rewrite_task", "rhythm_checks"):
            self.assertIn(f'"{field}"', user_prompt)
        for word in ("不默认高分", "不硬夸", "普通完成不应轻易给 8 分以上", "不要再输出人物、对话、场景、文采等独立维度分"):
            self.assertIn(word, combined)
        for key in ("hook", "pressure", "counter_expectation", "payoff", "follow_through"):
            self.assertIn(f'"{key}"', user_prompt)

    async def test_get_today_assignment_without_existing_daily_prompts_generation(self):
        generator = getattr(services, "generate_daily_assignment", None)
        self.assertIsNotNone(generator)
        if generator is None:
            return

        with patch.object(services, "generate_daily_assignment", AsyncMock()) as gen:
            result = await services.get_or_create_today_assignment(self.cfg)

        self.assertEqual(result["type"], "daily")
        self.assertTrue(result["needsGeneration"])
        self.assertEqual(result["date"], datetime.now().strftime("%Y-%m-%d"))
        self.assertIn("suggestedDimension", result)
        self.assertEqual(gen.await_count, 0)

    async def test_get_today_assignment_reuses_existing_daily_draft(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "today daily", "write from a scene", None, "节奏", f"{today}T00:00:00"),
            )
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        services.save_assignment_draft(aid, "saved daily draft")
        restored = await services.get_or_create_today_assignment(self.cfg)
        self.assertEqual(restored["id"], aid)
        self.assertEqual(restored["draftContent"], "saved daily draft")
        self.assertEqual(restored["draftCharCount"], len("saved daily draft"))

    async def test_daily_assignment_prefers_unsubmitted_after_submission(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "submitted daily", "old seed", None, "structure", f"{today}T00:00:00"),
            )
            submitted_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (submitted_id, today, "x" * 300, 300, "{}", "{}", f"{today}T00:01:00"),
            )
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "open daily", "new seed", None, "character", f"{today}T00:02:00"),
            )
            open_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        result = await services.get_or_create_today_assignment(self.cfg)

        self.assertEqual(result["id"], open_id)
        self.assertNotIn("submission", result)
        self.assertEqual(result["draftContent"], "")

    async def test_replace_today_daily_assignment_allows_new_after_submission_and_accepts_intent(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "submitted daily", "old seed", None, None, f"{today}T00:00:00"),
            )
            submitted_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (submitted_id, today, "x" * 300, 300, "{}", "{}", f"{today}T00:01:00"),
            )

        with patch.object(
            services,
            "generate_daily_assignment",
            AsyncMock(
                return_value={
                    "type": "daily",
                    "title": "new daily",
                    "scenario": "new seed",
                    "image_data": None,
                    "focus_dimension": None,
                }
            ),
        ) as gen:
            result = await services.replace_today_daily_assignment(self.cfg, intent="退婚流")

        self.assertNotEqual(result["id"], submitted_id)
        self.assertEqual(result["title"], "new daily")
        self.assertEqual(gen.await_count, 1)
        self.assertEqual(gen.await_args.args[3], "退婚流")

    def test_repeat_daily_assignment_copies_prompt_for_today(self):
        source_date = "2026-04-29"
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (source_date, "daily", "source daily", "source seed", None, "environment", f"{source_date}T00:00:00"),
            )
            source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        result = services.repeat_daily_assignment(source_id)

        self.assertNotEqual(result["id"], source_id)
        self.assertEqual(result["date"], today)
        self.assertEqual(result["type"], "daily")
        self.assertEqual(result["title"], "source daily")
        self.assertEqual(result["scenario"], "source seed")
        self.assertEqual(result["focusDimension"], "environment")
        self.assertEqual(result["draftContent"], "")

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
            services.save_assignment_draft(first["id"], "saved image draft")
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
        self.assertEqual(reused["draftContent"], "saved image draft")
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
            services.save_assignment_draft(first["id"], "discarded draft")
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
            draft_rows = conn.execute("SELECT * FROM assignment_drafts").fetchall()
        self.assertEqual([r["title"] for r in active], ["new image"])
        self.assertEqual(draft_rows, [])

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
            services.save_assignment_draft(first["id"], "saved outline draft")
            second = await creator(self.cfg)

        self.assertEqual(first["type"], "outline_practice")
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["draftContent"], "saved outline draft")
        self.assertTrue(first["due"])
        self.assertEqual(gen.await_count, 1)

    async def test_score_submission_deletes_assignment_draft(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "outline_practice", "score draft", "outline body", None, None, f"{today}T00:00:00"),
            )
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        services.save_assignment_draft(aid, "x" * 120)

        fake_provider = AsyncMock()
        fake_provider.chat = AsyncMock(return_value='{"scores": {}, "feedback": {}, "overall": "ok"}')
        with patch.object(services, "get_text_provider", return_value=fake_provider):
            await services.score_submission(aid, "x" * 120, self.cfg)

        with connect() as conn:
            draft = conn.execute("SELECT * FROM assignment_drafts WHERE assignment_id = ?", (aid,)).fetchone()
        self.assertIsNone(draft)

    async def test_score_submission_preserves_market_training_and_rewrite_task(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "score metadata", "seed", None, None, f"{today}T00:00:00"),
            )
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        fake_provider = AsyncMock()
        fake_provider.chat = AsyncMock(
            return_value="""
            {
              "market_score": 4,
              "training_score": 7,
              "fatal_problem": "主角没有主动反击，追读欲断掉",
              "best_part": "天雷降临前的停顿有画面感",
              "rewrite_task": {
                "target": "测出五行杂灵根后到天雷降临前",
                "requirement": "加入群嘲、主角一句反问、长老一句判死刑式压制、血滴石碑的停顿",
                "word_limit": "300字以内"
              },
              "scores": {},
              "feedback": {},
              "overall": "优先补压迫与反击。"
            }
            """
        )
        with patch.object(services, "get_text_provider", return_value=fake_provider):
            result = await services.score_submission(aid, "x" * 320, self.cfg)

        self.assertEqual(result["marketScore"], 4)
        self.assertEqual(result["trainingScore"], 7)
        self.assertEqual(result["fatalProblem"], "主角没有主动反击，追读欲断掉")
        self.assertEqual(result["bestPart"], "天雷降临前的停顿有画面感")
        self.assertEqual(result["rewriteTask"]["target"], "测出五行杂灵根后到天雷降临前")
        self.assertEqual(result["rewriteTask"]["wordLimit"], "300字以内")

        with connect() as conn:
            row = conn.execute("SELECT * FROM submissions WHERE assignment_id = ?", (aid,)).fetchone()
        restored = services.submission_row_to_dict(row)
        self.assertEqual(restored["marketScore"], 4)
        self.assertEqual(restored["trainingScore"], 7)
        self.assertEqual(restored["fatalProblem"], "主角没有主动反击，追读欲断掉")
        self.assertEqual(restored["rewriteTask"]["requirement"], "加入群嘲、主角一句反问、长老一句判死刑式压制、血滴石碑的停顿")

    async def test_score_submission_preserves_rhythm_score_and_checkpoints(self):
        today = datetime.now().strftime("%Y-%m-%d")
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO assignments (date, type, title, scenario, image_data, focus_dimension, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (today, "daily", "rhythm metadata", "seed", None, "节奏", f"{today}T00:00:00"),
            )
            aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        fake_provider = AsyncMock()
        fake_provider.chat = AsyncMock(
            return_value="""
            {
              "rhythm_score": 7,
              "market_score": 6,
              "training_score": 7,
              "fatal_problem": "爽点兑现太早，结尾没有追读钩子",
              "best_part": "宗门审判开场的压迫成立",
              "rewrite_task": {
                "target": "结尾反击段",
                "requirement": "把真正身份揭露延后，只先让审判长脸色变化",
                "word_limit": "300字以内"
              },
              "rhythm_checks": {
                "hook": {"status": "成立", "reason": "开场有明确审判危机"},
                "pressure": {"status": "成立", "reason": "长老和同门持续施压"},
                "counter_expectation": {"status": "偏弱", "reason": "主角可反击资源铺垫不足"},
                "payoff": {"status": "偏弱", "reason": "反击结果来得太快"},
                "follow_through": {"status": "缺失", "reason": "结尾没有新悬念"}
              },
              "overall": "节奏链前半段成立，后半段泄力。"
            }
            """
        )
        with patch.object(services, "get_text_provider", return_value=fake_provider):
            result = await services.score_submission(aid, "x" * 320, self.cfg)

        self.assertEqual(result["scores"], {"节奏": 7})
        self.assertEqual(result["rhythmChecks"]["hook"]["status"], "成立")
        self.assertEqual(result["rhythmChecks"]["followThrough"]["status"], "缺失")

        with connect() as conn:
            row = conn.execute("SELECT * FROM submissions WHERE assignment_id = ?", (aid,)).fetchone()
        restored = services.submission_row_to_dict(row)
        self.assertEqual(restored["scores"], {"节奏": 7})
        self.assertEqual(restored["rhythmChecks"]["payoff"]["status"], "偏弱")

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
                (daily_id, "2026-04-29", "daily text", 500, '{"节奏": 8}', '{"dims": {}, "overall": ""}', "2026-04-29T00:00:00"),
            )
            conn.execute(
                """
                INSERT INTO submissions
                  (assignment_id, date, content, char_count, scores, feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (image_id, "2026-04-29", "image text", 500, '{"节奏": 6}', '{"dims": {}, "overall": ""}', "2026-04-29T00:01:00"),
            )

        all_stats = services.collect_stats(mode="all")
        daily_stats = services.collect_stats(mode="daily")
        image_stats = services.collect_stats(mode="image_practice")

        self.assertEqual(len(all_stats["series"]), 2)
        self.assertEqual(len(daily_stats["series"]), 1)
        self.assertEqual(len(image_stats["series"]), 1)
        self.assertEqual(daily_stats["latest"]["节奏"], 8)
        self.assertEqual(image_stats["latest"]["节奏"], 6)

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
