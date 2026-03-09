"""
JWT (short-lived, 1h) + DPoP (RFC 9449) token binding — HARDENED.

Security changes:
  [S1] Fernet KDF uses PBKDF2 with proper salt instead of raw SHA-256
  [S2] Token creation uses timezone-aware datetimes
  [S3] Added token JTI generation for refresh token tracking
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import jwt as _jwt
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePublicKey, ECDSA
)
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat
)
from cryptography.exceptions import InvalidSignature
from loguru import logger

from app.core.config import settings

_utcnow = lambda: datetime.now(timezone.utc)  # noqa: E731


# ── JWT access tokens ─────────────────────────────────────────────────────────

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS   = 30
ALGORITHM                   = "HS256"


def _get_jwt_secret() -> str:
    """Unwrap SecretStr safely."""
    secret = settings.jwt_secret
    if hasattr(secret, "get_secret_value"):
        return secret.get_secret_value()
    return str(secret)


def create_access_token(
    user_id: str,
    tg_id: int,
    roles: list[str],
    jkt: Optional[str] = None,
) -> str:
    now = _utcnow()
    payload: dict[str, Any] = {
        "sub":   user_id,
        "tg_id": tg_id,
        "roles": roles,
        "iat":   now,
        "exp":   now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti":   secrets.token_urlsafe(16),
        "type":  "access",
    }
    if jkt:
        payload["cnf"] = {"jkt": jkt}
    return _jwt.encode(payload, _get_jwt_secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str, tg_id: int) -> str:
    now = _utcnow()
    payload = {
        "sub":  user_id,
        "tg_id": tg_id,
        "iat":  now,
        "exp":  now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "jti":  secrets.token_urlsafe(24),
        "type": "refresh",
    }
    return _jwt.encode(payload, _get_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return _jwt.decode(token, _get_jwt_secret(), algorithms=[ALGORITHM])


# ── DPoP helpers (RFC 9449) ───────────────────────────────────────────────────

def _b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def _jwk_thumbprint(jwk: dict) -> str:
    required = {k: jwk[k] for k in sorted(["crv", "kty", "x", "y"]) if k in jwk}
    canonical = json.dumps(required, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(hashlib.sha256(canonical).digest()).rstrip(b"=").decode()


def _load_ec_public_key(jwk: dict) -> EllipticCurvePublicKey:
    from cryptography.hazmat.primitives.asymmetric.ec import (
        EllipticCurvePublicNumbers, SECP256R1
    )
    x = int.from_bytes(_b64url_decode(jwk["x"]), "big")
    y = int.from_bytes(_b64url_decode(jwk["y"]), "big")
    pub_numbers = EllipticCurvePublicNumbers(x=x, y=y, curve=SECP256R1())
    return pub_numbers.public_key()


def validate_dpop_proof(
    proof_jwt: str,
    method: str,
    url: str,
    expected_jkt: Optional[str] = None,
    expected_nonce: Optional[str] = None,
) -> tuple[bool, str, Optional[str]]:
    try:
        header_b64 = proof_jwt.split(".")[0]
        header = json.loads(_b64url_decode(header_b64))

        if header.get("typ") != "dpop+jwt":
            return False, "Invalid typ, expected dpop+jwt", None
        if header.get("alg") not in ("ES256", "ES384", "ES512"):
            return False, "DPoP must use EC algorithm", None

        jwk = header.get("jwk")
        if not jwk or jwk.get("kty") != "EC":
            return False, "Missing or invalid JWK in header", None

        pub_key = _load_ec_public_key(jwk)
        jkt = _jwk_thumbprint(jwk)

        try:
            decoded = _jwt.decode(
                proof_jwt,
                pub_key,
                algorithms=["ES256", "ES384", "ES512"],
                options={"verify_exp": True},
            )
        except _jwt.ExpiredSignatureError:
            return False, "DPoP proof expired", None
        except _jwt.InvalidSignatureError:
            return False, "DPoP proof signature invalid", None

        if decoded.get("htm", "").upper() != method.upper():
            return False, f"htm mismatch: expected {method}", None
        if decoded.get("htu", "").rstrip("/") != url.rstrip("/"):
            return False, f"htu mismatch: expected {url}", None

        iat = decoded.get("iat", 0)
        if abs(time.time() - iat) > 60:
            return False, "DPoP proof too old or from the future", None

        if not decoded.get("jti"):
            return False, "Missing jti in DPoP proof", None

        if expected_nonce and decoded.get("nonce") != expected_nonce:
            return False, "DPoP nonce mismatch", None

        if expected_jkt and jkt != expected_jkt:
            return False, "DPoP key thumbprint does not match token cnf.jkt", None

        return True, "", jkt

    except Exception as exc:
        logger.warning(f"DPoP validation error: {exc}")
        return False, f"DPoP validation error: {exc}", None


def issue_dpop_nonce() -> str:
    return secrets.token_urlsafe(32)


# ── Telegram initData validation ──────────────────────────────────────────────

import hmac
import urllib.parse


def validate_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict[str, Any]]:
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
            
        token_str = bot_token.get_secret_value() if hasattr(bot_token, "get_secret_value") else bot_token

        secret_key = hmac.new(b"WebAppData", token_str.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 86400:
            logger.warning(f"Telegram initData expired (auth_date={auth_date})")
            return None

        user_str = parsed.get("user", "{}")
        return json.loads(user_str)

    except Exception as exc:
        logger.warning(f"initData validation failed: {exc}")
        return None


# ── API key helpers ───────────────────────────────────────────────────────────

import bcrypt


def generate_api_key() -> tuple[str, str, str]:
    raw = "ncfu_" + secrets.token_urlsafe(40)
    key_hash = bcrypt.hashpw(raw.encode(), bcrypt.gensalt(rounds=12)).decode()
    prefix = raw[:12]
    return raw, key_hash, prefix


def verify_api_key(raw_key: str, key_hash: str) -> bool:
    try:
        return bcrypt.checkpw(raw_key.encode(), key_hash.encode())
    except Exception:
        return False


# ── [S1] Fernet encryption with proper KDF ──────────────────────────────────

def _get_fernet():
    """Return a Fernet instance using PBKDF2-derived key from JWT secret."""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes

        jwt_secret = _get_jwt_secret()
        if not jwt_secret:
            return None

        # Use a fixed salt derived from the secret itself (deterministic)
        # This allows decryption across restarts without storing the salt separately
        salt = hashlib.sha256(b"ncfu-fernet-salt:" + jwt_secret[:8].encode()).digest()[:16]

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(jwt_secret.encode()))
        return Fernet(key)
    except ImportError:
        return None
    except Exception as exc:
        logger.warning(f"Fernet initialization failed: {exc}")
        return None


def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    if not f or not plaintext:
        return plaintext
    encrypted = f.encrypt(plaintext.encode()).decode()
    return f"enc:{encrypted}"


def decrypt_value(value: str) -> str:
    if not value or not value.startswith("enc:"):
        return value
    f = _get_fernet()
    if not f:
        return value
    try:
        return f.decrypt(value[4:].encode()).decode()
    except Exception:
        return value
