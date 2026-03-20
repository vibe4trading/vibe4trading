from __future__ import annotations

import secrets

import redis
from eth_utils.address import to_checksum_address

from v4t.settings import get_settings

_settings = get_settings()
_redis_client = redis.from_url(_settings.redis_url, decode_responses=True)

NONCE_TTL_SECONDS = 300


def generate_nonce() -> str:
    """Generate a cryptographically secure 64-character hex nonce."""
    return secrets.token_hex(32)


def store_nonce(wallet_address: str, nonce: str) -> None:
    """Store nonce in Redis with 5-minute TTL."""
    checksummed = to_checksum_address(wallet_address)
    key = f"wallet_nonce:{checksummed}:{nonce}"
    _redis_client.setex(key, NONCE_TTL_SECONDS, "1")


def verify_and_consume_nonce(wallet_address: str, nonce: str) -> bool:
    """Verify nonce exists and consume it (single-use enforcement)."""
    checksummed = to_checksum_address(wallet_address)
    key = f"wallet_nonce:{checksummed}:{nonce}"
    exists = _redis_client.delete(key)
    return exists > 0
