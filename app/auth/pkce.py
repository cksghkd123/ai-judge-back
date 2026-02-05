import hashlib
import secrets
from base64 import urlsafe_b64encode


def generate_state() -> str:
    """CSRF 방지를 위한 랜덤 state 문자열 생성."""
    return secrets.token_urlsafe(32)


def generate_code_verifier() -> str:
    """PKCE code_verifier 생성 (43~128자, [A-Za-z0-9-._~])."""
    return secrets.token_urlsafe(32)


def generate_code_challenge(code_verifier: str) -> str:
    """code_verifier로부터 S256 code_challenge 생성."""
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")
