"""
FrontierX Brain — API Authentication & Rate Limiting (Production Hardened)
========================================================================
Implements JWT validation, API key authentication, and IP-based rate limiting
using standard libraries only to ensure zero external dependency issues.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

try:
    from fastapi import Request, HTTPException, status, Security
    from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# ── Configuration (Environment Overrides) ──────────────────────
JWT_SECRET = os.getenv("FRONTIERX_JWT_SECRET", "prod-secure-jwt-secret-key-change-me")
VALID_API_KEYS = set(os.getenv("FRONTIERX_API_KEYS", "dev-api-key,robot-sensor-key").split(","))
RATE_LIMIT_CALLS = int(os.getenv("FRONTIERX_RATE_LIMIT_CALLS", "60"))       # 60 requests
RATE_LIMIT_PERIOD = int(os.getenv("FRONTIERX_RATE_LIMIT_PERIOD", "60"))    # per 60 seconds


# ── JWT Utility Functions (Standard Library Only) ───────────────
def base64url_decode(payload: str) -> bytes:
    """Decode base64url encoded string."""
    rem = len(payload) % 4
    if rem > 0:
        payload += "=" * (4 - rem)
    return base64.urlsafe_b64decode(payload)


def verify_jwt(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token using HMAC SHA256.
    Returns the payload dictionary if valid, None otherwise.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_segment, payload_segment, crypto_segment = parts
        header = json.loads(base64url_decode(header_segment).decode("utf-8"))
        payload = json.loads(base64url_decode(payload_segment).decode("utf-8"))

        # Verify algorithm
        if header.get("alg") != "HS256":
            return None

        # Verify signature
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        expected_signature = hmac.new(
            JWT_SECRET.encode("utf-8"),
            signing_input,
            hashlib.sha256
        ).digest()
        actual_signature = base64url_decode(crypto_segment)

        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        # Verify expiration
        exp = payload.get("exp")
        if exp and exp < time.time():
            return None

        return payload
    except Exception:
        return None


# ── Rate Limiter (Token Bucket Algorithm) ──────────────────────
class TokenBucketRateLimiter:
    """In-memory rate limiter using a sliding token bucket algorithm."""

    def __init__(self, limit: int, period: int) -> None:
        self.limit = limit
        self.period = period
        self.buckets: Dict[str, Tuple[float, float]] = defaultdict(lambda: (float(limit), time.time()))

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        tokens, last_update = self.buckets[client_ip]

        # Calculate refill
        elapsed = now - last_update
        refill = elapsed * (self.limit / self.period)
        new_tokens = min(float(self.limit), tokens + refill)

        if new_tokens >= 1.0:
            self.buckets[client_ip] = (new_tokens - 1.0, now)
            return True
        else:
            self.buckets[client_ip] = (new_tokens, now)
            return False


rate_limiter = TokenBucketRateLimiter(RATE_LIMIT_CALLS, RATE_LIMIT_PERIOD)


# ── FastAPI Dependencies (Only exposed if FastAPI is available) ──
if FASTAPI_AVAILABLE:
    api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    bearer_scheme = HTTPBearer(auto_error=False)

    async def get_current_user(
        api_key: Optional[str] = Security(api_key_header),
        bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
    ) -> dict:
        """
        Authenticate requests via:
        1. X-API-Key HTTP Header (ideal for robots/scripts)
        2. JWT Bearer Token in Authorization Header (ideal for users/dashboard)
        """
        # 1. Try API Key Auth
        if api_key:
            if api_key in VALID_API_KEYS:
                return {"auth_type": "api_key", "identity": "robot_client"}
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key"
            )

        # 2. Try JWT Bearer Auth
        if bearer_token:
            payload = verify_jwt(bearer_token.credentials)
            if payload:
                return {"auth_type": "jwt", "identity": payload.get("sub", "unknown_user"), "scopes": payload.get("scopes", [])}
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT Bearer Token"
            )

        # No auth credentials provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide X-API-Key or Bearer Token."
        )

    async def check_rate_limit(request: Request) -> None:
        """fastapi dependency verifying client IP is within rate limits."""
        client_ip = request.client.host if request.client else "127.0.0.1"
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again in a minute."
            )
else:
    # Fallback placeholders for dependency injection mock environments
    async def get_current_user() -> dict:
        return {"auth_type": "none", "identity": "anonymous"}

    async def check_rate_limit() -> None:
        pass
