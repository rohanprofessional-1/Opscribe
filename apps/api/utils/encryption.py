import os
from cryptography.fernet import Fernet
from dotenv import dotenv_values

# Load configuration
env = dotenv_values(os.path.join(os.path.dirname(__file__), "..", ".env"))
MASTER_KEY = env.get("OPSCRIBE_MASTER_KEY") or os.environ.get("OPSCRIBE_MASTER_KEY")

if not MASTER_KEY:
    # If starting fresh, provide instructions. In production, this must be set.
    print("WARNING: OPSCRIBE_MASTER_KEY not found in .env! Generating an ephemeral key for this session.")
    print("WARNING: Client integrations saved during this session cannot be decrypted if the server restarts.")
    MASTER_KEY = Fernet.generate_key().decode("utf-8")

# Initialize cipher suite
cipher_suite = Fernet(MASTER_KEY.encode("utf-8"))

def encrypt_value(value: str) -> str:
    """Encrypt a plaintext string."""
    if not value:
        return value
    return cipher_suite.encrypt(value.encode("utf-8")).decode("utf-8")

def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string."""
    if not encrypted_value:
        return encrypted_value
    try:
        return cipher_suite.decrypt(encrypted_value.encode("utf-8")).decode("utf-8")
    except Exception as e:
        print(f"ERROR: Failed to decrypt value. Was the OPSCRIBE_MASTER_KEY changed? {e}")
        return ""

def encrypt_dict(data: dict, keys_to_encrypt: list[str]) -> dict:
    """Returns a new dictionary with specified keys encrypted."""
    result = data.copy()
    for key in keys_to_encrypt:
        if key in result and isinstance(result[key], str):
            result[key] = encrypt_value(result[key])
    return result

def decrypt_dict(data: dict, keys_to_encrypt: list[str]) -> dict:
    """Returns a new dictionary with specified keys decrypted."""
    result = data.copy()
    for key in keys_to_encrypt:
        if key in result and isinstance(result[key], str):
            result[key] = decrypt_value(result[key])
    return result
