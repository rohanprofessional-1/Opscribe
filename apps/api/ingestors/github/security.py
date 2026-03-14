import os
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)
_encryption_key = os.environ.get("GITHUB_ENCRYPTION_KEY")
if not _encryption_key:
    logger.warning("GITHUB_ENCRYPTION_KEY not set! we'll use fallback temporary key for dev only. !")
    _encryption_key = b'P9_zF1E_6vX1J2A3b4C5d6E7f8G9h0I1j2K3l4M5n6o='

_fernet = Fernet(_encryption_key)

def encrypt_token(token: str) -> str:
    if not token:
        return ""
    return _fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    return _fernet.decrypt(encrypted_token.encode()).decode()
