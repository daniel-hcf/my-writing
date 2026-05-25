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
        self.assertIn("换一题再写", source)
        self.assertIn("api.repeatDailyAssignment", source)
        self.assertIn("api.newAssignment", source)
        self.assertIn("renderAssignment(root, ctx, next)", source)
