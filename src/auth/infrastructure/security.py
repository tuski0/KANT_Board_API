import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from dotenv import load_dotenv

from auth.domain.entities import TokenPayload
from auth.domain.service import TokenProvider
from shared.core.exceptions import UnauthorizedException

# JWT_SECRET_KEY, JWT_EXPIRE_MINUTES 를 .env 에서 읽기 위해 먼저 로드
load_dotenv()

class JwtTokenProvider(TokenProvider):
    def __init__(
        self,
        # HS512 권장 규격에 맞춰 최소 64바이트(512비트) 이상의 시크릿 키 권장
        secret_key: str = os.getenv("JWT_SECRET_KEY", "your-at-least-64-bytes-long-super-secure-secret-key-for-hs512-algorithm-safety!"),
        algorithm: str = "HS512",
        access_token_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = access_token_expire_minutes

    def create_access_token(self, user_id: int) -> tuple[str, str, datetime, int]:
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.expire_minutes)
        expired_at = now + expires_delta
        expires_in = int(expires_delta.total_seconds())
        jti = str(uuid.uuid4())

        payload = {
            "sub": str(user_id),
            "jti": jti,
            "exp": expired_at,
            "iat": now,
        }
        encoded_jwt = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt, jti, expired_at, expires_in

    def decode_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(
                user_id=int(payload["sub"]),  # sub 는 문자열 → 정수로 변환
                jti=payload["jti"],
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            )
        except (jwt.PyJWTError, KeyError, ValueError):
            raise UnauthorizedException("유효하지 않거나 만료된 토큰입니다.")