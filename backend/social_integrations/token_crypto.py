"""Token encryption for stored social OAuth credentials.

Access and refresh tokens are encrypted with Fernet before database
persistence and decrypted only in-memory at use time. Key resolution:
explicit SOCIAL_TOKEN_KEY, else derived from the application SECRET_KEY.
Ciphertext is stored prefixed with ``fernet:``; values without the prefix
are rejected (fail closed, prompting reconnect) rather than used raw.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings

logger = logging.getLogger(__name__)

PREFIX = "fernet:"


def _fernet() -> Fernet:
    """Build the Fernet cipher from configured key material."""
    raw = (settings.SOCIAL_TOKEN_KEY or "").strip()
    if raw:
        key = raw.encode("utf-8")
    else:
        if not settings.SECRET_KEY:
            raise ValueError("No SOCIAL_TOKEN_KEY or SECRET_KEY configured for token encryption")
        key = base64.urlsafe_b64encode(hashlib.sha256((settings.SECRET_KEY + "::social-tokens").encode("utf-8")).digest())
    return Fernet(key)


class TokenDecryptionError(ValueError):
    """Raised when a stored token cannot be decrypted (reconnect required)."""


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token for storage. Returns ``fernet:<ciphertext>``."""
    if not plaintext:
        raise ValueError("Cannot encrypt an empty token")
    return PREFIX + _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_token(stored: str) -> str:
    """Decrypt a stored token. Rejects unprefixed (legacy plaintext) values."""
    if not stored or not stored.startswith(PREFIX):
        raise TokenDecryptionError(
            "Stored credential is not encrypted; please reconnect the account"
        )
    try:
        return _fernet().decrypt(stored[len(PREFIX):].encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise TokenDecryptionError("Stored credential failed integrity check") from exc
