from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    jti: str
    exp: datetime


@dataclass
class BlacklistToken:
    jti: str
    expired_at: datetime