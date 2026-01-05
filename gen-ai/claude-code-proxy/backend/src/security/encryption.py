import boto3
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

from ..config import get_settings


class KMSEnvelopeEncryption:
    """KMS envelope encryption for Bedrock API keys."""

    def __init__(self, kms_key_id: str | None = None, region: str | None = None):
        settings = get_settings()
        self._kms_key_id = kms_key_id or settings.kms_key_id
        self._local_key = self._get_local_key(settings)
        self._kms = None
        if self._kms_key_id:
            self._kms = boto3.client("kms", region_name=region or settings.bedrock_region)

    def _get_local_key(self, settings) -> bytes | None:
        if settings.local_encryption_key:
            return hashlib.sha256(settings.local_encryption_key.encode()).digest()
        if settings.key_hasher_secret:
            return hashlib.sha256(settings.key_hasher_secret.encode()).digest()
        if settings.jwt_secret:
            return hashlib.sha256(settings.jwt_secret.encode()).digest()
        return None

    def encrypt(self, plaintext: str) -> bytes:
        if not self._kms_key_id:
            if not self._local_key:
                raise ValueError(
                    "Local encryption key is not configured. "
                    "Set PROXY_LOCAL_ENCRYPTION_KEY (or PROXY_KEY_HASHER_SECRET/PROXY_JWT_SECRET) "
                    "for local-only mode."
                )
            nonce = os.urandom(12)
            aesgcm = AESGCM(self._local_key)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
            return nonce + ciphertext

        # Generate data key
        response = self._kms.generate_data_key(KeyId=self._kms_key_id, KeySpec="AES_256")
        data_key = response["Plaintext"]
        encrypted_data_key = response["CiphertextBlob"]

        # Encrypt with data key
        nonce = os.urandom(12)
        aesgcm = AESGCM(data_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

        # Return: encrypted_data_key_len (2 bytes) + encrypted_data_key + nonce + ciphertext
        edk_len = len(encrypted_data_key).to_bytes(2, "big")
        return edk_len + encrypted_data_key + nonce + ciphertext

    def decrypt(self, blob: bytes) -> str:
        if not self._kms_key_id:
            if not self._local_key:
                raise ValueError(
                    "Local encryption key is not configured. "
                    "Set PROXY_LOCAL_ENCRYPTION_KEY (or PROXY_KEY_HASHER_SECRET/PROXY_JWT_SECRET) "
                    "for local-only mode."
                )
            nonce = blob[:12]
            ciphertext = blob[12:]
            aesgcm = AESGCM(self._local_key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode()

        # Parse blob
        edk_len = int.from_bytes(blob[:2], "big")
        encrypted_data_key = blob[2 : 2 + edk_len]
        nonce = blob[2 + edk_len : 2 + edk_len + 12]
        ciphertext = blob[2 + edk_len + 12 :]

        # Decrypt data key with KMS
        response = self._kms.decrypt(CiphertextBlob=encrypted_data_key)
        data_key = response["Plaintext"]

        # Decrypt with data key
        aesgcm = AESGCM(data_key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        return plaintext.decode()
