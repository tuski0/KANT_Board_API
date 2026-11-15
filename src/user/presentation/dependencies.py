from user.application.service import UserService
from user.domain.repository import UserRepository
from user.domain.user import User

# 실제 구현은 wiring/user.py 에서 app.dependency_overrides 로 연결


def provide_user_service() -> UserService:
    raise NotImplementedError("UserService 의존성이 주입되지 않았습니다.")


def provide_user_repository() -> UserRepository:
    raise NotImplementedError("UserRepository 의존성이 주입되지 않았습니다.")


async def get_current_user() -> User:
    raise NotImplementedError("get_current_user 의존성이 주입되지 않았습니다.")


async def get_optional_user() -> User | None:
    raise NotImplementedError("get_optional_user 의존성이 주입되지 않았습니다.")


async def require_admin() -> User:
    raise NotImplementedError("require_admin 의존성이 주입되지 않았습니다.")
