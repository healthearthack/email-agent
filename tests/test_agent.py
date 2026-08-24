import importlib.util
import os
from email.message import EmailMessage
from pathlib import Path
import sys
import types
import unittest

# These unit tests exercise parser/filter logic without requiring network packages.
# GitHub Actions separately installs requirements.txt before executing the live agent.
try:
    import markdown  # noqa: F401
except ImportError:
    markdown_stub = types.ModuleType("markdown")
    markdown_stub.markdown = lambda text, extensions=None: text
    sys.modules["markdown"] = markdown_stub

try:
    from google import genai  # noqa: F401
except (ImportError, ModuleNotFoundError):
    google_stub = sys.modules.setdefault("google", types.ModuleType("google"))
    genai_stub = types.ModuleType("google.genai")
    genai_stub.Client = lambda *args, **kwargs: None
    google_stub.genai = genai_stub
    sys.modules["google.genai"] = genai_stub

try:
    import simple_salesforce  # noqa: F401
except ImportError:
    sf_stub = types.ModuleType("simple_salesforce")
    sf_stub.Salesforce = object
    sys.modules["simple_salesforce"] = sf_stub

os.environ.setdefault("GMAIL_USER", "agent@example.com")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("DRAFT_ONLY_MODE", "True")

MODULE_PATH = Path(__file__).resolve().parents[1] / "metaknews@gmail.com.py"
spec = importlib.util.spec_from_file_location("metaknews_agent", MODULE_PATH)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


class AutomatedSenderFilterTests(unittest.TestCase):
    def message(self, **headers):
        msg = EmailMessage()
        for key, value in headers.items():
            msg[key.replace("_", "-")] = value
        return msg

    def test_notification_subdomain_is_filtered(self):
        self.assertTrue(agent.is_automated_or_spam("usbank@notifications.usbank.com", self.message()))

    def test_no_reply_is_filtered(self):
        self.assertTrue(agent.is_automated_or_spam("no-reply@example.com", self.message()))

    def test_list_unsubscribe_is_filtered(self):
        msg = self.message(List_Unsubscribe="<mailto:unsubscribe@example.com>")
        self.assertTrue(agent.is_automated_or_spam("news@example.com", msg))

    def test_auto_submitted_is_filtered(self):
        msg = self.message(Auto_Submitted="auto-generated")
        self.assertTrue(agent.is_automated_or_spam("person@example.com", msg))

    def test_human_sender_is_allowed(self):
        self.assertFalse(agent.is_automated_or_spam("person@example.com", self.message()))

    def test_self_sender_is_filtered(self):
        self.assertTrue(agent.is_automated_or_spam("agent@example.com", self.message()))


class ParsingTests(unittest.TestCase):
    def test_encoded_subject(self):
        self.assertEqual(agent.clean_subject("=?utf-8?q?Hello_=E2=98=80?="), "Hello ☀")

    def test_sender_name(self):
        first, last, addr = agent.parse_sender_name("Jane Q. Developer <jane@example.com>")
        self.assertEqual((first, last, addr), ("Jane", "Q. Developer", "jane@example.com"))


if __name__ == "__main__":
    unittest.main()
