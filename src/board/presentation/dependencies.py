from board.application.service import BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from board.domain.repository.board_repository import BoardRepository
from board.domain.repository.comment_repository import CommentRepository
from board.domain.repository.post_repository import PostRepository

# 실제 구현은 wiring/board.py 에서 app.dependency_overrides 로 연결


# Repository 의존성
def provide_board_repository() -> BoardRepository:
    raise NotImplementedError("BoardRepository 의존성이 주입되지 않았습니다.")


def provide_post_repository() -> PostRepository:
    raise NotImplementedError("PostRepository 의존성이 주입되지 않았습니다.")


def provide_comment_repository() -> CommentRepository:
    raise NotImplementedError("CommentRepository 의존성이 주입되지 않았습니다.")


# Service 의존성
def provide_board_service() -> BoardService:
    raise NotImplementedError("BoardService 의존성이 주입되지 않았습니다.")


def provide_post_service() -> PostService:
    raise NotImplementedError("PostService 의존성이 주입되지 않았습니다.")


def provide_comment_service() -> CommentService:
    raise NotImplementedError("CommentService 의존성이 주입되지 않았습니다.")


async def get_current_role() -> Role | None:
    """
    현재 요청자의 권한 (열람용, 로그인 선택)
    - 비회원: None
    - 로그인 일반회원: Role.USER
    - 관리자: Role.ADMIN
    """
    raise NotImplementedError("get_current_role 의존성이 주입되지 않았습니다.")


async def get_member_role() -> Role:
    """로그인 필수 요청자의 권한 (작성·수정·삭제용, 비로그인은 401)"""
    raise NotImplementedError("get_member_role 의존성이 주입되지 않았습니다.")


async def get_current_author() -> Author:
    """로그인 필수 작성자 정보 (비로그인은 401)"""
    raise NotImplementedError("get_current_author 의존성이 주입되지 않았습니다.")


async def require_admin_role() -> Role:
    """게시판 설정 변경 등을 위한 관리자 권한 검증"""
    raise NotImplementedError("require_admin_role 의존성이 주입되지 않았습니다.")
