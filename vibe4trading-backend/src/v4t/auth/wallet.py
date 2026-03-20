"""Wallet signature verification for Ethereum addresses."""

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils.address import to_checksum_address


def verify_wallet_signature(wallet_address: str, message: str, signature: str) -> bool:
    """
    Verify an Ethereum wallet signature.

    Args:
        wallet_address: Ethereum address (any case)
        message: Plain text message that was signed
        signature: Hex-encoded signature string

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Validate Chain ID is Ethereum Mainnet (chainId: 1)
        if "Chain ID: 1" not in message:
            return False

        # Encode message for EIP-191 personal_sign format
        encoded_message = encode_defunct(text=message)

        # Recover signer address from signature
        recovered_address = Account.recover_message(encoded_message, signature=signature)

        # Normalize both addresses to EIP-55 checksummed format
        normalized_wallet = to_checksum_address(wallet_address)
        normalized_recovered = to_checksum_address(recovered_address)

        # Compare normalized addresses
        return normalized_wallet == normalized_recovered
    except Exception:
        return False
