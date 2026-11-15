from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from board.application.service import BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from board.domain.repository.board_repository import BoardRepository
from board.domain.repository.comment_repository import CommentRepository
from board.domain.repository.post_repository import PostRepository
from board.infrastructure.sqlalchemy.board_repository import SqlAlchemyBoardRepository
from board.infrastructure.sqlalchemy.comment_repository import SqlAlchemyCommentRepository
from board.infrastructure.sqlalchemy.post_repository import SqlAlchemyPostRepository
from board.presentation.dependencies import (
    get_current_author,
    get_current_role,
    get_member_role,
    provide_board_repository,
    provide_board_service,
    provide_comment_repository,
    provide_comment_service,
    provide_post_repository,
    provide_post_service,
    require_admin_role,
)
from shared.core.database import get_db
from shared.core.exceptions import ForbiddenException
from user.domain.user import User
from wiring.user import resolve_current_user, resolve_optional_user


def create_board_repository(session: AsyncSession = Depends(get_db)) -> BoardRepository:
    return SqlAlchemyBoardRepository(session)


def create_post_repository(session: AsyncSession = Depends(get_db)) -> PostRepository:
    return SqlAlchemyPostRepository(session)


def create_comment_repository(session: AsyncSession = Depends(get_db)) -> CommentRepository:
    return SqlAlchemyCommentRepository(session)


def create_board_service(repo: BoardRepository = Depends(create_board_repository)) -> BoardService:
    return BoardService(board_repo=repo)


def create_post_service(
    post_repo: PostRepository = Depends(create_post_repository),
    board_repo: BoardRepository = Depends(create_board_repository),
) -> PostService:
    return PostService(post_repo=post_repo, board_repo=board_repo)


def create_comment_service(
    comment_repo: CommentRepository = Depends(create_comment_repository),
    post_repo: PostRepository = Depends(create_post_repository),
    board_repo: BoardRepository = Depends(create_board_repository),
) -> CommentService:
    return CommentService(comment_repo=comment_repo, post_repo=post_repo, board_repo=board_repo)


# 열람용: 비로그인이면 None
async def _get_current_role(user: User | None = Depends(resolve_optional_user)) -> Role | None:
    return Role(user.role) if user else None


# 작성·수정·삭제용: 비로그인이면 resolve_current_user 에서 401
async def _get_member_role(user: User = Depends(resolve_current_user)) -> Role:
    return Role(user.role)


async def _get_current_author(user: User = Depends(resolve_current_user)) -> Author:
    return Author.member(user_id=user.id, username=user.name)


async def _require_admin_role(role: Role = Depends(_get_member_role)) -> Role:
    if role != Role.ADMIN:
        raise ForbiddenException("관리자 권한이 필요합니다.")
    return role


def wire_board_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_board_repository: create_board_repository,
            provide_post_repository: create_post_repository,
            provide_comment_repository: create_comment_repository,
            provide_board_service: create_board_service,
            provide_post_service: create_post_service,
            provide_comment_service: create_comment_service,
            get_current_role: _get_current_role,
            get_member_role: _get_member_role,
            get_current_author: _get_current_author,
            require_admin_role: _require_admin_role,
        }
    )
