from auth.domain.service import UserCredentialVerifier
from user.domain.repository import UserRepository
from user.domain.service import PasswordHasher


class UserCredentialVerifierImpl(UserCredentialVerifier):
    def __init__(self, user_repo: UserRepository, password_hasher: PasswordHasher):
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    async def verify_credentials(self, email: str, plain_password: str) -> int | None:
        user = await self._user_repo.find_by_email(email)
        # 없는 회원이거나 탈퇴한 회원은 로그인 불가
        if not user or user.is_withdrawn:
            return None

        if not self._password_hasher.verify(plain_password, user.password_hash):
            return None

        return user.id