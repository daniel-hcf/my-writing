import os
import sys
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ENCRYPTED_PREFIX = "enc:v1:"
ENV_KEY = "MY_WRITING_ENCRYPTION_KEY"


def is_encrypted(value: str) -> bool:
    return value.startswith(ENCRYPTED_PREFIX)


def encrypt_secret(value: str) -> str:
    if not value or is_encrypted(value):
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return ENCRYPTED_PREFIX + token


def decrypt_secret(value: str) -> str:
    if not value or not is_encrypted(value):
        return value
    token = value.removeprefix(ENCRYPTED_PREFIX)
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Cannot decrypt saved AI API key. Restore the original encryption key "
            "or re-enter the API key in settings."
        ) from exc


def _fernet() -> Fernet:
    key = os.environ.get(ENV_KEY)
    if key:
        return _build_fernet(key.encode("ascii"), f"{ENV_KEY} environment variable")
    return _build_fernet(_load_or_create_key(), str(_key_path()))


def _build_fernet(key: bytes, source: str) -> Fernet:
    try:
        return Fernet(key)
    except Exception as exc:
        raise RuntimeError(f"Invalid encryption key from {source}.") from exc


def _load_or_create_key() -> bytes:
    path = _key_path()
    if path.exists():
        return path.read_bytes().strip()

    path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    path.write_bytes(key)
    _restrict_permissions(path)
    return key


def _key_path() -> Path:
    if sys.platform == "win32":
        root = os.environ.get("APPDATA")
        base = Path(root) if root else Path.home() / "AppData" / "Roaming"
        return base / "my-writing" / "secret.key"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "my-writing" / "secret.key"
    root = os.environ.get("XDG_CONFIG_HOME")
    base = Path(root) if root else Path.home() / ".config"
    return base / "my-writing" / "secret.key"


def _restrict_permissions(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
