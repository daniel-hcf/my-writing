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
