from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from v4t.auth.nonce import generate_nonce, store_nonce, verify_and_consume_nonce
from v4t.auth.wallet import verify_wallet_signature
from v4t.db.models import UserRow


@pytest.fixture
def test_wallet():
    """Generate a test wallet with private key."""
    account = Account.create()
    return {
        "address": account.address,
        "private_key": account.key.hex(),
        "account": account,
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client for nonce storage."""
    with patch("v4t.auth.nonce._redis_client") as mock:
        mock.setex = MagicMock()
        mock.delete = MagicMock(return_value=1)
        yield mock


# Nonce generation and storage tests
def test_generate_nonce():
    """Test nonce generation produces 64-char hex string."""
    nonce = generate_nonce()
    assert len(nonce) == 64
    assert all(c in "0123456789abcdef" for c in nonce)


def test_store_nonce(mock_redis):
    """Test nonce storage in Redis with TTL."""
    wallet = "0x1234567890123456789012345678901234567890"
    nonce = "abc123"

    store_nonce(wallet, nonce)

    mock_redis.setex.assert_called_once_with(f"wallet_nonce:{wallet}:{nonce}", 300, "1")


def test_verify_and_consume_nonce_valid(mock_redis):
    """Test valid nonce verification and consumption."""
    wallet = "0x1234567890123456789012345678901234567890"
    nonce = "abc123"
    mock_redis.delete.return_value = 1

    result = verify_and_consume_nonce(wallet, nonce)

    assert result is True
    mock_redis.delete.assert_called_once_with(f"wallet_nonce:{wallet}:{nonce}")


def test_verify_and_consume_nonce_invalid(mock_redis):
    """Test invalid/expired nonce returns False."""
    wallet = "0x1234567890123456789012345678901234567890"
    nonce = "expired"
    mock_redis.delete.return_value = 0

    result = verify_and_consume_nonce(wallet, nonce)

    assert result is False


# Signature verification tests
def test_verify_wallet_signature_valid(test_wallet):
    """Test valid signature verification."""
    message = "Sign in to Vibe4Trading\n\nNonce: test123\nChain ID: 1"
    encoded = encode_defunct(text=message)
    signed = test_wallet["account"].sign_message(encoded)

    result = verify_wallet_signature(test_wallet["address"], message, signed.signature.hex())

    assert result is True


def test_verify_wallet_signature_invalid_signature(test_wallet):
    """Test invalid signature returns False."""
    message = "Sign in to Vibe4Trading\n\nNonce: test123\nChain ID: 1"
    bad_signature = "0x" + "00" * 65

    result = verify_wallet_signature(test_wallet["address"], message, bad_signature)

    assert result is False


def test_verify_wallet_signature_wrong_message(test_wallet):
    """Test signature for different message returns False."""
    message1 = "Sign in to Vibe4Trading\n\nNonce: test123\nChain ID: 1"
    message2 = "Sign in to Vibe4Trading\n\nNonce: different\nChain ID: 1"

    encoded = encode_defunct(text=message1)
    signed = test_wallet["account"].sign_message(encoded)

    result = verify_wallet_signature(test_wallet["address"], message2, signed.signature.hex())

    assert result is False


def test_verify_wallet_signature_case_insensitive(test_wallet):
    """Test signature verification works with different address cases."""
    message = "Sign in to Vibe4Trading\n\nNonce: test123\nChain ID: 1"
    encoded = encode_defunct(text=message)
    signed = test_wallet["account"].sign_message(encoded)

    result = verify_wallet_signature(
        test_wallet["address"].lower(), message, signed.signature.hex()
    )

    assert result is True


# /auth/wallet/challenge endpoint tests
def test_wallet_challenge_success(client: TestClient, mock_redis):
    """Test challenge endpoint generates nonce."""
    res = client.post(
        "/auth/wallet/challenge",
        json={"wallet_address": "0x1234567890123456789012345678901234567890"},
    )

    assert res.status_code == 200
    data = res.json()
    assert "nonce" in data
    assert "message" in data
    assert len(data["nonce"]) == 64
    assert "Sign in to Vibe4Trading" in data["message"]
    assert data["nonce"] in data["message"]
    mock_redis.setex.assert_called_once()


def test_wallet_challenge_invalid_address(client: TestClient):
    """Test challenge with invalid address returns 400."""
    res = client.post("/auth/wallet/challenge", json={"wallet_address": "invalid"})

    assert res.status_code == 400
    assert "Invalid wallet address" in res.json()["detail"]


# /auth/wallet/verify endpoint tests
def test_wallet_verify_success_new_user(
    client: TestClient, db_session: Session, test_wallet, mock_redis
):
    """Test verify creates new user and sets session cookie."""
    nonce = "test_nonce_123"
    message = f"Sign in to Vibe4Trading\n\nNonce: {nonce}\nChain ID: 1"
    encoded = encode_defunct(text=message)
    signed = test_wallet["account"].sign_message(encoded)

    mock_redis.delete.return_value = 1

    res = client.post(
        "/auth/wallet/verify",
        json={
            "wallet_address": test_wallet["address"],
            "signature": signed.signature.hex(),
            "nonce": nonce,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert "user_id" in data
    assert data["wallet_address"] == test_wallet["address"]
    assert "v4t_session" in res.cookies


def test_wallet_verify_invalid_nonce(client: TestClient, test_wallet, mock_redis):
    """Test verify with expired nonce returns 400."""
    mock_redis.delete.return_value = 0

    res = client.post(
        "/auth/wallet/verify",
        json={
            "wallet_address": test_wallet["address"],
            "signature": "0x" + "00" * 65,
            "nonce": "expired_nonce",
        },
    )

    assert res.status_code == 400
    assert "Invalid or expired nonce" in res.json()["detail"]


def test_wallet_verify_invalid_signature(client: TestClient, test_wallet, mock_redis):
    """Test verify with invalid signature returns 401."""
    nonce = "test_nonce_456"
    mock_redis.delete.return_value = 1

    res = client.post(
        "/auth/wallet/verify",
        json={
            "wallet_address": test_wallet["address"],
            "signature": "0x" + "00" * 65,
            "nonce": nonce,
        },
    )

    assert res.status_code == 401
    assert "Invalid signature" in res.json()["detail"]


def test_wallet_verify_existing_user(
    client: TestClient, db_session: Session, test_wallet, mock_redis
):
    """Test verify with existing wallet user."""
    user = UserRow(wallet_address=test_wallet["address"])
    db_session.add(user)
    db_session.commit()

    nonce = "test_nonce_789"
    message = f"Sign in to Vibe4Trading\n\nNonce: {nonce}\nChain ID: 1"
    encoded = encode_defunct(text=message)
    signed = test_wallet["account"].sign_message(encoded)

    mock_redis.delete.return_value = 1

    res = client.post(
        "/auth/wallet/verify",
        json={
            "wallet_address": test_wallet["address"],
            "signature": signed.signature.hex(),
            "nonce": nonce,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == str(user.user_id)


# /me/link-wallet endpoint tests
def test_link_wallet_success(client: TestClient, db_session: Session, test_wallet, mock_redis):
    """Test linking wallet to existing user."""
    user = UserRow(
        oidc_issuer="test", oidc_sub="link-user", email="link@example.com", display_name="Link User"
    )
    db_session.add(user)
    db_session.commit()

    nonce = "link_nonce_123"
    message = f"Sign in to Vibe4Trading\n\nNonce: {nonce}\nChain ID: 1"
    encoded = encode_defunct(text=message)
    signed = test_wallet["account"].sign_message(encoded)

    mock_redis.delete.return_value = 1

    res = client.post(
        "/me/link-wallet",
        json={
            "wallet_address": test_wallet["address"],
            "signature": signed.signature.hex(),
            "nonce": nonce,
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["wallet_address"] == test_wallet["address"]

    db_session.refresh(user)
    assert user.wallet_address == test_wallet["address"]


def test_link_wallet_invalid_nonce(client: TestClient, db_session: Session, mock_redis):
    """Test link wallet with expired nonce returns 400."""
    user = UserRow(oidc_issuer="test", oidc_sub="nonce-user", email="nonce@example.com")
    db_session.add(user)
    db_session.commit()

    mock_redis.delete.return_value = 0

    res = client.post(
        "/me/link-wallet",
        json={
            "wallet_address": "0x1234567890123456789012345678901234567890",
            "signature": "0x" + "00" * 65,
            "nonce": "expired",
        },
    )

    assert res.status_code == 400
    assert "Invalid or expired nonce" in res.json()["detail"]


def test_link_wallet_invalid_signature(
    client: TestClient, db_session: Session, test_wallet, mock_redis
):
    """Test link wallet with invalid signature returns 401."""
    user = UserRow(oidc_issuer="test", oidc_sub="sig-user", email="sig@example.com")
    db_session.add(user)
    db_session.commit()

    mock_redis.delete.return_value = 1

    res = client.post(
        "/me/link-wallet",
        json={
            "wallet_address": test_wallet["address"],
            "signature": "0x" + "00" * 65,
            "nonce": "test_nonce",
        },
    )

    assert res.status_code == 401
    assert "Invalid signature" in res.json()["detail"]


def test_link_wallet_already_linked_to_another_user(
    client: TestClient, db_session: Session, test_wallet, mock_redis
):
    """Test linking wallet already owned by another user returns 409."""
    current_user = UserRow(oidc_issuer="test", oidc_sub="current-user", email="current@example.com")
    other_user = UserRow(
        oidc_issuer="test",
        oidc_sub="other-user",
        email="other@example.com",
        wallet_address=test_wallet["address"],
    )
    db_session.add(current_user)
    db_session.add(other_user)
    db_session.commit()

    nonce = "conflict_nonce"
    message = f"Sign in to Vibe4Trading\n\nNonce: {nonce}\nChain ID: 1"
    encoded = encode_defunct(text=message)
    signed = test_wallet["account"].sign_message(encoded)

    mock_redis.delete.return_value = 1

    res = client.post(
        "/me/link-wallet",
        json={
            "wallet_address": test_wallet["address"],
            "signature": signed.signature.hex(),
            "nonce": nonce,
        },
    )

    assert res.status_code == 409
    assert "already linked" in res.json()["detail"]


# /me/unlink-wallet endpoint tests
def test_unlink_wallet_success(client: TestClient, db_session: Session):
    """Test unlinking wallet from user."""
    user = UserRow(
        oidc_issuer="test",
        oidc_sub="unlink-user",
        email="unlink@example.com",
        wallet_address="0x1234567890123456789012345678901234567890",
    )
    db_session.add(user)
    db_session.commit()

    res = client.post("/me/unlink-wallet")

    assert res.status_code == 200
    assert res.json()["success"] is True

    db_session.refresh(user)
    assert user.wallet_address is None
