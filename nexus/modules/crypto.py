import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# This key should be loaded from a secure environment variable.
# For DEV, we can fallback to a generated one if missing, but print a warning.
MASTER_KEY_B64 = os.getenv("MOBIUS_MASTER_KEY")

if not MASTER_KEY_B64:
    # Generate a key for first-time use (Development convenience)
    # In PROD, this must be set explicitly.
    print("WARNING: MOBIUS_MASTER_KEY not set. Generating a temporary one.")
    _key = AESGCM.generate_key(bit_length=256)
    MASTER_KEY = _key
    print(f"Generated Temporary MASTER_KEY (Save this to .env): {base64.urlsafe_b64encode(_key).decode()}")
else:
    try:
        MASTER_KEY = base64.urlsafe_b64decode(MASTER_KEY_B64)
    except Exception as e:
        raise ValueError(f"Invalid MOBIUS_MASTER_KEY format: {e}")

aesgcm = AESGCM(MASTER_KEY)

def encrypt(plaintext: str) -> str:
    """
    Encrypts a plaintext string using AES-GCM.
    Returns: 'nonce:ciphertext' both base64 encoded.
    """
    if not plaintext:
        return ""
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    
    # Pack as nonce:ciphertext
    return f"{base64.urlsafe_b64encode(nonce).decode()}:{base64.urlsafe_b64encode(ciphertext).decode()}"

def decrypt(payload: str) -> str:
    """
    Decrypts a payload formatted as 'nonce:ciphertext'
    """
    if not payload or ":" not in payload:
        return payload # Return raw if not encrypted (migration support)
        
    try:
        b64_nonce, b64_ciphertext = payload.split(":", 1)
        nonce = base64.urlsafe_b64decode(b64_nonce)
        ciphertext = base64.urlsafe_b64decode(b64_ciphertext)
        
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception as e:
        print(f"Decryption failed: {e}")
        return "[ENCRYPTED_DATA_ERROR]"
