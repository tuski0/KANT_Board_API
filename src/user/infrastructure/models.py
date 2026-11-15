from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from shared.core.models import Base, DateTimeBase
from user.domain.user import User, UserStatus


class UserModel(Base, DateTimeBase):
    __tablename__ = "users"

    # PK: DB 자동 증가 정수
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)
    # 회원 상태: ACTIVE(정상), WITHDRAWN(탈퇴)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE.value, nullable=False)

    def to_user(self) -> User:
        """ORM Model -> Domain Entity 변환"""
        return User(
            id=self.id,
            email=self.email,
            name=self.name,
            password_hash=self.password_hash,
            role=self.role,
            status=UserStatus(self.status),
            created_at=self.created_at,
            modified_at=self.modified_at,
            deleted_at=self.deleted_at,
        )