import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet

from my_writing import db, outlines
from my_writing.db import connect, init_db
from my_writing.models import FullConfig, ProviderConfig


def make_cfg() -> FullConfig:
    return FullConfig(
        text=ProviderConfig(provider="openai", apiKey="sk-text", baseUrl="https://example.com", model="gpt-4o"),
        image=ProviderConfig(provider="openai", apiKey="", baseUrl="https://example.com", model="gpt-image-1"),
    )


class OutlineCoachTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "data.db")
        self.key = Fernet.generate_key().decode()
        self.env = patch.dict(os.environ, {"MY_WRITING_ENCRYPTION_KEY": self.key}, clear=False)
        self.env.start()
        self.db_patch = patch.object(db, "DB_PATH", self.db_path)
        self.db_patch.start()
        init_db()

    def tearDown(self):
        self.db_patch.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_init_db_creates_outline_tables(self):
        with connect() as conn:
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'outline_%'"
                ).fetchall()
            }

        self.assertEqual(
            {
                "outline_projects",
                "outline_characters",
                "outline_volumes",
                "outline_chapters",
                "outline_reviews",
            },
            tables,
        )

    def test_projects_are_isolated_and_restore_outline_state(self):
        first = outlines.create_project(
            {
                "title": "雷法归来",
                "genre": "玄幻",
                "premise": "废柴重掌雷法",
                "mainGoal": "夺回内门名额",
                "corePayoff": "连续打脸",
            }
        )
        second = outlines.create_project({"title": "末世商人", "genre": "末世"})

        outlines.update_characters(
            first["id"],
            {
                "protagonistIdentity": "被废灵根的外门弟子",
                "protagonistGoal": "三个月内重回内门",
                "protagonistWeakness": "修为被废",
                "protagonistGrowth": "用雷法重新立威",
                "antagonistIdentity": "抢走名额的师兄",
                "antagonistReason": "害怕真相暴露",
                "antagonistPressure": "断资源并公开羞辱",
            },
        )
        outlines.update_volume(
            first["id"],
            {
                "title": "重回内门",
                "goal": "拿回考核资格",
                "pressure": "所有资源被断",
                "payoff": "第一次公开反击",
                "endingHook": "发现陷害者背后还有长老",
                "openingHook": "退婚当日被逐出宗门",
                "midpointEscalation": "唯一证人被收买",
                "finalExplosion": "考核台上逆转",
            },
        )
        outlines.update_chapter(
            first["id"],
            1,
            {
                "title": "退婚当日",
                "summary": "主角被逼交出内门令",
                "payoff": "用残存雷意震住众人",
                "hook": "令牌里传出师尊遗言",
                "draft": "正文草稿",
            },
        )

        restored = outlines.get_project(first["id"])
        other = outlines.get_project(second["id"])

        self.assertEqual(restored["characters"]["protagonistGoal"], "三个月内重回内门")
        self.assertEqual(restored["volume"]["endingHook"], "发现陷害者背后还有长老")
        self.assertEqual(restored["chapters"][0]["draft"], "正文草稿")
        self.assertEqual(other["characters"]["protagonistGoal"], "")
        self.assertEqual(other["volume"]["endingHook"], "")
        self.assertEqual(other["chapters"][0]["title"], "")

    def test_updating_chapter_draft_does_not_overwrite_outline_fields(self):
        project = outlines.create_project({"title": "只改正文"})
        outlines.update_chapter(
            project["id"],
            1,
            {
                "title": "第一章",
                "summary": "主角遇阻",
                "payoff": "第一次反击",
                "hook": "新敌人出现",
            },
        )

        outlines.update_chapter(project["id"], 1, {"draft": "正文第一版"})

        chapter = outlines.get_project(project["id"])["chapters"][0]
        self.assertEqual(chapter["title"], "第一章")
        self.assertEqual(chapter["summary"], "主角遇阻")
        self.assertEqual(chapter["draft"], "正文第一版")

    async def test_review_persists_feedback_without_changing_user_outline(self):
        project = outlines.create_project({"title": "点评测试", "premise": "主角翻身"})
        before = outlines.get_project(project["id"])
        fake_provider = AsyncMock()
        fake_provider.chat = AsyncMock(
            return_value='{"issues":["阻碍者动机不够具体"],"questions":["他为什么必须阻止主角？"],"suggestions":["补充利益冲突"]}'
        )

        with patch.object(outlines, "get_text_provider", return_value=fake_provider):
            review = await outlines.review_project(project["id"], "core", make_cfg())

        after = outlines.get_project(project["id"])
        self.assertEqual(after["title"], before["title"])
        self.assertEqual(after["premise"], before["premise"])
        self.assertEqual(review["scope"], "core")
        self.assertEqual(review["issues"], ["阻碍者动机不够具体"])
        self.assertEqual(after["reviews"][0]["suggestions"], ["补充利益冲突"])


if __name__ == "__main__":
    unittest.main()
