import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class FrontendContractsTest(unittest.TestCase):
    def test_editorial_dashboard_clears_root_before_rerendering(self):
        source = (ROOT / "web" / "js" / "views" / "editorial.js").read_text(encoding="utf-8")

        self.assertRegex(
            source,
            r"async function renderDashboard\(root\) \{\s+root\.innerHTML = \"\";",
        )

    def test_sent_briefs_can_be_resent_from_history(self):
        source = (ROOT / "web" / "js" / "views" / "editorial.js").read_text(encoding="utf-8")

        self.assertIn('brief.status === "sent" ? "重新发送" : "发送邮件"', source)
        self.assertNotIn("sendBtn.disabled = brief.status === \"sent\"", source)

    def test_editorial_page_makes_regeneration_visible(self):
        source = (ROOT / "web" / "js" / "views" / "editorial.js").read_text(encoding="utf-8")

        self.assertIn("重新生成今日简报", source)
        self.assertIn("brief.createdAt", source)
        self.assertIn("brief.sentAt", source)
        self.assertIn("briefBtn.disabled = false", source)

    def test_practice_drafts_are_exposed_in_frontend_api(self):
        source = (ROOT / "web" / "js" / "api.js").read_text(encoding="utf-8")

        self.assertIn("saveDraft", source)
        self.assertIn("deleteDraft", source)
        self.assertIn("/draft", source)

    def test_daily_repeat_endpoint_is_exposed_in_frontend_api(self):
        source = (ROOT / "web" / "js" / "api.js").read_text(encoding="utf-8")

        self.assertIn("repeatDailyAssignment", source)
        self.assertIn("/repeat", source)

    def test_daily_new_assignment_accepts_optional_intent(self):
        source = (ROOT / "web" / "js" / "api.js").read_text(encoding="utf-8")

        self.assertIn("newAssignment: (intent", source)
        self.assertIn("{ intent }", source)

    def test_scored_practice_views_use_backend_drafts(self):
        for name in ("daily.js", "image_practice.js", "outline_practice.js"):
            source = (ROOT / "web" / "js" / "views" / name).read_text(encoding="utf-8")
            with self.subTest(view=name):
                self.assertIn("assignment.draftContent", source)
                self.assertIn("createDraftController", source)
                self.assertIn("buildDraftControls", source)
                self.assertIn("api.deleteDraft", source)
                self.assertIn("confirmDiscardDraft", source)

    def test_daily_result_view_offers_repeat_and_new_prompt_actions(self):
        source = (ROOT / "web" / "js" / "views" / "daily.js").read_text(encoding="utf-8")

        self.assertIn("再写同一题", source)
        self.assertIn("换题材再练节奏", source)
        self.assertIn("api.repeatDailyAssignment", source)
        self.assertIn("renderGenerationPrompt(root, ctx)", source)
        self.assertIn("renderAssignment(root, ctx, next)", source)

    def test_daily_view_shows_scene_intent_generation_entry(self):
        source = (ROOT / "web" / "js" / "views" / "daily.js").read_text(encoding="utf-8")

        self.assertIn("今天想用什么题材/场景练节奏？", source)
        self.assertIn("退婚流、宗门审判、都市打脸、末世抢物资", source)
        self.assertIn("assignment.needsGeneration", source)
        self.assertIn("api.newAssignment(intent", source)

    def test_scored_results_surface_rhythm_chain(self):
        common = (ROOT / "web" / "js" / "views" / "practice_common.js").read_text(encoding="utf-8")

        for label in ("节奏链诊断", "钩子是否立住", "压迫是否推进", "反击期待是否形成", "爽点是否兑现", "结尾是否留下追读"):
            self.assertIn(label, common)

    def test_scored_results_surface_market_signals_and_rewrite_task(self):
        common = (ROOT / "web" / "js" / "views" / "practice_common.js").read_text(encoding="utf-8")
        for label in ("市场追读", "练习完成", "最致命问题", "最佳部分", "下一稿任务", "rewriteTask"):
            self.assertIn(label, common)

        for name in ("history.js", "journal.js"):
            source = (ROOT / "web" / "js" / "views" / name).read_text(encoding="utf-8")
            with self.subTest(view=name):
                self.assertIn("renderMarketSignals", source)

    def test_outline_coach_frontend_contracts_are_exposed(self):
        index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
        api = (ROOT / "web" / "js" / "api.js").read_text(encoding="utf-8")
        view_path = ROOT / "web" / "js" / "views" / "long_outline.js"

        self.assertTrue(view_path.exists())
        view = view_path.read_text(encoding="utf-8")

        self.assertIn('data-tab="long_outline"', index)
        self.assertIn("renderLongOutline", app)
        for method in (
            "listOutlineProjects",
            "createOutlineProject",
            "getOutlineProject",
            "updateOutlineProject",
            "deleteOutlineProject",
            "updateOutlineCharacters",
            "updateOutlineVolume",
            "updateOutlineChapter",
            "reviewOutlineProject",
            "reviewOutlineChapter",
        ):
            self.assertIn(method, api)
        for label in ("引导填写", "大纲总览", "章节开写", "轻量人物", "前10章章节纲"):
            self.assertIn(label, view)
