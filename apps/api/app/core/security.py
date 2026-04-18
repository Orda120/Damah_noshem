from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _serializer() -> URLSafeTimedSerializer:
    settings = get_settings()
    return URLSafeTimedSerializer(settings.jwt_secret, salt="damah-session")


def create_session_token(app_user_id: UUID) -> str:
    return _serializer().dumps(
        {"app_user_id": str(app_user_id), "issued_at": datetime.now(UTC).isoformat()}
    )


def decode_session_token(token: str) -> UUID | None:
    settings = get_settings()
    try:
        payload = _serializer().loads(token, max_age=settings.session_max_age_seconds)
    except (BadSignature, BadTimeSignature):
        return None
    try:
        return UUID(payload["app_user_id"])
    except (KeyError, ValueError, TypeError):
        return None
