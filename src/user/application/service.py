import uuid

from sqlalchemy.exc import IntegrityError

from shared.core.exceptions import ConflictException, NotFoundException
from user.domain.repository import UserRepository
from user.domain.service import PasswordHasher
from user.domain.user import User


class UserService:
    def __init__(self, repository: UserRepository, hasher: PasswordHasher):
        self.repository = repository
        self.hasher = hasher

    async def register_user(self, email: str, name: str, password: str) -> User:
        # 이메일 중복 체크
        if await self.repository.find_by_email(email):
            raise ConflictException(
                message="이미 사용 중인 이메일입니다.",
                error_code="EMAIL_ALREADY_EXISTS",
            )

        # 엔티티 생성 (형식/길이/비밀번호 규칙 검증 → 실패하면 ValidationException 그대로 전달)
        user = User.create(
            email=email,
            name=name,
            raw_password=password,
            hasher=self.hasher,
        )
        try:
            return await self.repository.save(user)
        except IntegrityError as err:
            # 동시에 같은 이메일로 가입한 경우 (UNIQUE 제약 위반)
            raise ConflictException(
                message="이미 사용 중인 이메일입니다.",
                error_code="EMAIL_ALREADY_EXISTS",
            ) from err

    async def create_admin_if_absent(self, email: str, name: str, password: str) -> User:
        """서버 시작 시 관리자 계정 준비 (이미 있으면 그대로 반환)"""
        existing = await self.repository.find_by_email(email)
        if existing:
            return existing
        admin = User.create(email=email, name=name, raw_password=password, hasher=self.hasher, role="ADMIN")
        return await self.repository.save(admin)

    async def get_user(self, user_id: uuid.UUID) -> User:
        user = await self.repository.find_by_id(user_id)
        if not user:
            raise NotFoundException(message="사용자를 찾을 수 없습니다.", error_code="USER_NOT_FOUND")
        return user

    async def change_password(
        self,
        user_id: uuid.UUID,
        old_password: str,
        new_password: str,
    ) -> None:
        user = await self.get_user(user_id)
        user.change_password(
            old_password=old_password,
            new_password=new_password,
            hasher=self.hasher,
        )
        await self.repository.save(user)

    async def withdraw(self, target_user_id: uuid.UUID, requester: User) -> None:
        """회원 탈퇴 (소프트 삭제) - 본인 또는 관리자"""
        user = await self.get_user(target_user_id)
        user.withdraw(requester=requester)
        await self.repository.save(user)
