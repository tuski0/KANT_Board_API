import math

from fastapi import APIRouter, Depends, Query, status

from board.application.service import BoardService, CommentService, PostService
from board.domain.enums import Role
from board.domain.post import Author
from board.presentation.dependencies import (
    get_current_author,
    get_current_role,
    get_member_role,
    provide_board_service,
    provide_comment_service,
    provide_post_service,
    require_admin_role,
)
from board.presentation.schemas import (
    BoardResponse,
    CommentResponse,
    CreateBoardRequest,
    CreateCommentRequest,
    CreatePostRequest,
    PostDetailResponse,
    PostListItemResponse,
    PostPaginationResponse,
    PostSearchQuery,
    UpdateBoardRequest,
    UpdateCommentRequest,
    UpdatePostRequest,
)
from shared.core.schemas import APIResponse

router = APIRouter(prefix="/v1")

# 401/403/404 공통 응답 형식을 Swagger 문서에 표시
AUTH_ERRORS = {
    401: {"model": APIResponse[None], "description": "로그인 필요 / 토큰 오류"},
    403: {"model": APIResponse[None], "description": "권한 없음 (작성자 아님 등)"},
    404: {"model": APIResponse[None], "description": "리소스 없음"},
}


# 게시판 설정
@router.post(
    "/boards",
    response_model=BoardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="게시판 생성 (관리자 전용)",
    tags=["Boards"],
    responses=AUTH_ERRORS,
)
async def create_board(
    req: CreateBoardRequest,
    _: Role = Depends(require_admin_role),
    board_service: BoardService = Depends(provide_board_service),
) -> BoardResponse:
    board = await board_service.create_board(
        board_id=req.board_id,
        board_name=req.board_name,
        authority=req.authority.to_domain(),
        page_size=req.page_size,
    )
    return BoardResponse.from_domain(board)


@router.get("/boards", response_model=list[BoardResponse], summary="게시판 전체 목록 조회", tags=["Boards"])
async def list_boards(
    include_deleted: bool = Query(default=False, description="삭제된 게시판 포함 여부"),
    board_service: BoardService = Depends(provide_board_service),
) -> list[BoardResponse]:
    boards = await board_service.get_all_boards(include_deleted=include_deleted)
    return [BoardResponse.from_domain(board) for board in boards]


@router.get(
    "/boards/{board_id}",
    response_model=BoardResponse,
    summary="게시판 단건 조회",
    tags=["Boards"],
    responses={404: AUTH_ERRORS[404]},
)
async def get_board(
    board_id: str,
    board_service: BoardService = Depends(provide_board_service),
) -> BoardResponse:
    board = await board_service.get_board(board_id)
    return BoardResponse.from_domain(board)


@router.put(
    "/boards/{board_id}",
    response_model=BoardResponse,
    summary="게시판 설정 수정 (관리자 전용)",
    tags=["Boards"],
    responses=AUTH_ERRORS,
)
async def update_board_config(
    board_id: str,
    req: UpdateBoardRequest,
    _: Role = Depends(require_admin_role),
    board_service: BoardService = Depends(provide_board_service),
) -> BoardResponse:
    board = await board_service.update_board_config(
        board_id=board_id,
        board_name=req.board_name,
        page_size=req.page_size,
        authority=req.authority.to_domain() if req.authority else None,
    )
    return BoardResponse.from_domain(board)


@router.delete(
    "/boards/{board_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="게시판 삭제 (관리자 전용)",
    tags=["Boards"],
    responses=AUTH_ERRORS,
)
async def delete_board(
    board_id: str,
    _: Role = Depends(require_admin_role),
    board_service: BoardService = Depends(provide_board_service),
) -> None:
    await board_service.delete_board(board_id)


# 게시글
@router.post(
    "/boards/{board_id}/posts",
    response_model=PostDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="게시글 작성 (로그인 필요)",
    tags=["Posts"],
    responses=AUTH_ERRORS,
)
async def write_post(
    board_id: str,
    req: CreatePostRequest,
    author: Author = Depends(get_current_author),
    role: Role = Depends(get_member_role),
    post_service: PostService = Depends(provide_post_service),
) -> PostDetailResponse:
    post = await post_service.write_post(
        board_id=board_id,
        title=req.title,
        content=req.content,
        author=author,
        user_role=role,
    )
    return PostDetailResponse.from_domain(post)


@router.get(
    "/boards/{board_id}/posts",
    response_model=PostPaginationResponse,
    summary="게시글 목록 (페이징·검색)",
    tags=["Posts"],
    responses=AUTH_ERRORS,
)
async def list_posts(
    board_id: str,
    search_params: PostSearchQuery = Depends(),
    current_role: Role | None = Depends(get_current_role),
    post_service: PostService = Depends(provide_post_service),
) -> PostPaginationResponse:
    posts, total_count, page_size = await post_service.list_posts(
        board_id=board_id,
        user_role=current_role,
        page=search_params.page,
        page_size=search_params.page_size,
        search_type=search_params.search_type,
        keyword=search_params.keyword,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    return PostPaginationResponse(
        items=[PostListItemResponse.from_domain(post) for post in posts],
        total_count=total_count,
        page=search_params.page,
        page_size=page_size,
        total_pages=total_pages,
        search_type=search_params.search_type,
        keyword=search_params.keyword,
    )


@router.get(
    "/posts/{post_id}",
    response_model=PostDetailResponse,
    summary="게시글 상세 조회",
    tags=["Posts"],
    responses=AUTH_ERRORS,
)
async def get_post_detail(
    post_id: int,
    current_role: Role | None = Depends(get_current_role),
    post_service: PostService = Depends(provide_post_service),
) -> PostDetailResponse:
    post = await post_service.get_post_detail(post_id=post_id, user_role=current_role)
    return PostDetailResponse.from_domain(post)


@router.put(
    "/posts/{post_id}",
    response_model=PostDetailResponse,
    summary="게시글 수정 (작성자 또는 관리자)",
    tags=["Posts"],
    responses=AUTH_ERRORS,
)
async def update_post(
    post_id: int,
    req: UpdatePostRequest,
    author: Author = Depends(get_current_author),
    role: Role = Depends(get_member_role),
    post_service: PostService = Depends(provide_post_service),
) -> PostDetailResponse:
    post = await post_service.update_post(
        post_id=post_id,
        title=req.title,
        content=req.content,
        requester_id=author.author_id,
        user_role=role,
    )
    return PostDetailResponse.from_domain(post)


@router.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="게시글 삭제 (작성자 또는 관리자)",
    tags=["Posts"],
    responses=AUTH_ERRORS,
)
async def delete_post(
    post_id: int,
    author: Author = Depends(get_current_author),
    role: Role = Depends(get_member_role),
    post_service: PostService = Depends(provide_post_service),
) -> None:
    await post_service.delete_post(post_id=post_id, requester_id=author.author_id, user_role=role)


# 댓글
@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="댓글 작성 (로그인 필요)",
    tags=["Comments"],
    responses=AUTH_ERRORS,
)
async def write_comment(
    post_id: int,
    req: CreateCommentRequest,
    author: Author = Depends(get_current_author),
    role: Role = Depends(get_member_role),
    comment_service: CommentService = Depends(provide_comment_service),
) -> CommentResponse:
    comment = await comment_service.write_comment(
        post_id=post_id,
        content=req.content,
        author=author,
        user_role=role,
    )
    return CommentResponse.from_domain(comment)


@router.get(
    "/posts/{post_id}/comments",
    response_model=list[CommentResponse],
    summary="게시글의 댓글 목록",
    tags=["Comments"],
    responses=AUTH_ERRORS,
)
async def list_comments(
    post_id: int,
    current_role: Role | None = Depends(get_current_role),
    comment_service: CommentService = Depends(provide_comment_service),
) -> list[CommentResponse]:
    comments = await comment_service.list_comments(post_id=post_id, user_role=current_role)
    return [CommentResponse.from_domain(comment) for comment in comments]


@router.put(
    "/comments/{comment_id}",
    response_model=CommentResponse,
    summary="댓글 수정 (작성자 또는 관리자)",
    tags=["Comments"],
    responses=AUTH_ERRORS,
)
async def update_comment(
    comment_id: int,
    req: UpdateCommentRequest,
    author: Author = Depends(get_current_author),
    role: Role = Depends(get_member_role),
    comment_service: CommentService = Depends(provide_comment_service),
) -> CommentResponse:
    comment = await comment_service.update_comment(
        comment_id=comment_id,
        content=req.content,
        requester_id=author.author_id,
        user_role=role,
    )
    return CommentResponse.from_domain(comment)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="댓글 삭제 (작성자 또는 관리자)",
    tags=["Comments"],
    responses=AUTH_ERRORS,
)
async def delete_comment(
    comment_id: int,
    author: Author = Depends(get_current_author),
    role: Role = Depends(get_member_role),
    comment_service: CommentService = Depends(provide_comment_service),
) -> None:
    await comment_service.delete_comment(comment_id=comment_id, requester_id=author.author_id, user_role=role)
