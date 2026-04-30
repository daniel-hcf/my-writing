import os
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from my_writing.secret_store import (
    ENCRYPTED_PREFIX,
    decrypt_secret,
    encrypt_secret,
    is_encrypted,
)


class SecretStoreTest(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key().decode()
        self.env = patch.dict(os.environ, {"MY_WRITING_ENCRYPTION_KEY": self.key}, clear=False)
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_encrypt_secret_hides_plaintext_and_decrypts(self):
        encrypted = encrypt_secret("sk-test-secret")

        self.assertTrue(encrypted.startswith(ENCRYPTED_PREFIX))
        self.assertNotIn("sk-test-secret", encrypted)
        self.assertEqual(decrypt_secret(encrypted), "sk-test-secret")

    def test_encrypt_secret_is_idempotent(self):
        encrypted = encrypt_secret("sk-test-secret")

        self.assertEqual(encrypt_secret(encrypted), encrypted)
        self.assertTrue(is_encrypted(encrypted))

    def test_empty_and_legacy_plaintext_values_are_supported(self):
        self.assertEqual(encrypt_secret(""), "")
        self.assertEqual(decrypt_secret(""), "")
        self.assertEqual(decrypt_secret("legacy-plain-key"), "legacy-plain-key")


if __name__ == "__main__":
    unittest.main()
