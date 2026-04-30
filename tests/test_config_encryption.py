import json
import os
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from my_writing import db
from my_writing.db import get_config, init_db, set_config
from my_writing.models import FullConfig
from my_writing.routers.config import MASK, get_config_endpoint, put_config_endpoint
from my_writing.secret_store import ENCRYPTED_PREFIX
from my_writing.services import load_full_config, migrate_config_secrets


class ConfigEncryptionTest(unittest.TestCase):
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

    def test_put_config_encrypts_api_keys_and_load_decrypts_them(self):
        payload = FullConfig.model_validate(
            {
                "text": {
                    "provider": "openai",
                    "apiKey": "sk-text-secret",
                    "baseUrl": "https://api.openai.com/v1",
                    "model": "gpt-4o",
                },
                "image": {
                    "provider": "openai",
                    "apiKey": "sk-image-secret",
                    "baseUrl": "https://api.openai.com/v1",
                    "model": "gpt-image-1",
                },
            }
        )

        self.assertEqual(put_config_endpoint(payload), {"ok": True})

        raw_text = get_config("text")
        raw_image = get_config("image")
        self.assertTrue(raw_text["apiKey"].startswith(ENCRYPTED_PREFIX))
        self.assertTrue(raw_image["apiKey"].startswith(ENCRYPTED_PREFIX))
        self.assertNotIn("sk-text-secret", json.dumps(raw_text))
        self.assertNotIn("sk-image-secret", json.dumps(raw_image))

        cfg = load_full_config()
        self.assertEqual(cfg.text.apiKey, "sk-text-secret")
        self.assertEqual(cfg.image.apiKey, "sk-image-secret")

        response = get_config_endpoint()
        self.assertEqual(response["text"]["apiKey"], MASK)
        self.assertEqual(response["image"]["apiKey"], MASK)

    def test_masked_or_empty_api_key_preserves_existing_encrypted_value(self):
        set_config(
            "text",
            {
                "provider": "openai",
                "apiKey": "sk-existing-text",
                "baseUrl": "https://api.openai.com/v1",
                "model": "gpt-4o",
            },
        )
        set_config(
            "image",
            {
                "provider": "openai",
                "apiKey": "sk-existing-image",
                "baseUrl": "https://api.openai.com/v1",
                "model": "gpt-image-1",
            },
        )

        payload = FullConfig.model_validate(
            {
                "text": {
                    "provider": "openai",
                    "apiKey": MASK,
                    "baseUrl": "https://api.openai.com/v1",
                    "model": "gpt-5",
                },
                "image": {
                    "provider": "openai",
                    "apiKey": "",
                    "baseUrl": "https://api.openai.com/v1",
                    "model": "gpt-image-1",
                },
            }
        )

        put_config_endpoint(payload)

        cfg = load_full_config()
        self.assertEqual(cfg.text.apiKey, "sk-existing-text")
        self.assertEqual(cfg.image.apiKey, "sk-existing-image")
        self.assertEqual(cfg.text.model, "gpt-5")

    def test_migrate_config_secrets_rewrites_legacy_plaintext_api_keys(self):
        set_config(
            "text",
            {
                "provider": "openai",
                "apiKey": "sk-legacy-text",
                "baseUrl": "https://api.openai.com/v1",
                "model": "gpt-4o",
            },
        )
        set_config(
            "image",
            {
                "provider": "openai",
                "apiKey": "sk-legacy-image",
                "baseUrl": "https://api.openai.com/v1",
                "model": "gpt-image-1",
            },
        )

        migrate_config_secrets()

        raw_text = get_config("text")
        raw_image = get_config("image")
        self.assertTrue(raw_text["apiKey"].startswith(ENCRYPTED_PREFIX))
        self.assertTrue(raw_image["apiKey"].startswith(ENCRYPTED_PREFIX))
        self.assertNotIn("sk-legacy-text", json.dumps(raw_text))
        self.assertNotIn("sk-legacy-image", json.dumps(raw_image))
        self.assertEqual(load_full_config().text.apiKey, "sk-legacy-text")


if __name__ == "__main__":
    unittest.main()
