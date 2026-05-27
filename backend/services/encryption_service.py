"""
Encryption service — delegates to utils.credentials for a single encryption path (CRIT-003).
Legacy PBKDF2 decrypt is handled inside utils.credentials.decrypt_credential.
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.utils.credentials import decrypt_credential, encrypt_credential

logger = logging.getLogger(__name__)


class EncryptionService:
    """Thin wrapper kept for legacy provider_service imports."""

    def encrypt_credential(self, plaintext: str, key_id: str = "default") -> str:
        del key_id
        return encrypt_credential(plaintext)

    def decrypt_credential(self, ciphertext: str, key_id: str = "default") -> str:
        del key_id
        return decrypt_credential(ciphertext)


_encryption_service: Optional[EncryptionService] = None


def get_encryption_service(master_key: Optional[str] = None) -> EncryptionService:
    del master_key
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
