import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from board.domain.enums import Role
from shared.core.exceptions import BadRequestException, ValidationException

"""
1. 글과 댓글은 로그인한 회원만 작성할 수 있다. (비회원 작성 미지원)
2. 글·댓글은 작성한 회원 본인만 수정·삭제할 수 있고, 관리자는 모두 가능하다.
3. 삭제는 소프트 삭제(deleted_at 기록)로 처리한다.
"""


# Value Object 정의 S
@dataclass(frozen=True)
class BoardInfo:
    """게시판 정보 값 객체"""
    board_id: str
    board_name: str


@dataclass(frozen=True)
class Author:
    """작성자(회원) 정보 값 객체"""
    author_id: uuid.UUID
    author_name: str

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}

        if self.author_id is None:
            field_errors.setdefault("author_id", []).append("작성자는 로그인한 회원이어야 합니다.")

        if not self.author_name or not self.author_name.strip():
            field_errors.setdefault("author_name", []).append("작성자 이름은 필수 입력값입니다.")
        elif not (1 <= len(self.author_name.strip()) <= 50):
            field_errors.setdefault("author_name", []).append("작성자 이름은 1자 이상 50자 이하여야 합니다.")

        if field_errors:
            raise ValidationException(
                message="작성자 정보 유효성 검사에 실패했습니다.",
                field_errors=field_errors,
            )

    @classmethod
    def member(cls, user_id: uuid.UUID, username: str) -> "Author":
        """회원 작성자 생성"""
        return cls(author_id=user_id, author_name=username.strip())

    def is_owner(self, user_id: uuid.UUID | None) -> bool:
        """로그인 사용자가 작성자 본인인지 검증"""
        return user_id is not None and self.author_id == user_id


def _can_modify(author: Author, requester_id: uuid.UUID | None, user_role: Role | None) -> bool:
    """수정/삭제 권한: 관리자 → 작성자 본인 순으로 확인"""
    if user_role == Role.ADMIN:
        return True
    return author.is_owner(requester_id)
# Value Object 정의 E


# Entities 정의 S
@dataclass
class Post:
    """게시글 엔티티"""
    board_info: BoardInfo
    title: str
    content: str
    author: Author
    post_id: int | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}

        if not self.title or not self.title.strip():
            field_errors.setdefault("title", []).append("제목은 필수 입력값입니다.")

        if not self.content or not self.content.strip():
            field_errors.setdefault("content", []).append("내용은 필수 입력값입니다.")

        if self.post_id is not None and self.post_id < 1:
            field_errors.setdefault("post_id", []).append("게시글 ID는 1 이상의 정수여야 합니다.")

        if field_errors:
            raise ValidationException(
                message="게시글 유효성 검사에 실패했습니다.",
                field_errors=field_errors,
            )

    @classmethod
    def create(
        cls,
        board_id: str,
        board_name: str,
        title: str,
        content: str,
        author: Author,
    ) -> "Post":
        """신규 게시글 생성 도메인 팩토리"""
        return cls(
            board_info=BoardInfo(board_id=board_id, board_name=board_name),
            title=title.strip(),
            content=content.strip(),
            author=author,
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update_content(self, title: str, content: str) -> None:
        if self.is_deleted:
            raise BadRequestException(message="삭제된 게시글은 수정할 수 없습니다.")

        field_errors: dict[str, list[str]] = {}
        if not title or not title.strip():
            field_errors.setdefault("title", []).append("제목은 공백일 수 없습니다.")
        if not content or not content.strip():
            field_errors.setdefault("content", []).append("내용은 공백일 수 없습니다.")

        if field_errors:
            raise ValidationException(
                message="게시글 수정 유효성 검사에 실패했습니다.",
                field_errors=field_errors,
            )

        self.title = title.strip()
        self.content = content.strip()
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException("이미 삭제된 게시글입니다.")
        self.deleted_at = datetime.now(timezone.utc)

    def can_modify_or_delete(self, requester_id: uuid.UUID | None, user_role: Role | None) -> bool:
        return _can_modify(self.author, requester_id, user_role)


@dataclass
class Comment:
    """댓글 엔티티"""
    post_id: int
    content: str
    author: Author
    comment_id: int | None = None

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}

        if self.post_id < 1:
            field_errors.setdefault("post_id", []).append("유효한 게시글 ID여야 합니다.")

        if not self.content or not self.content.strip():
            field_errors.setdefault("content", []).append("댓글 내용은 필수 입력값입니다.")

        if self.comment_id is not None and self.comment_id < 1:
            field_errors.setdefault("comment_id", []).append("댓글 ID는 1 이상의 정수여야 합니다.")

        if field_errors:
            raise ValidationException(
                message="댓글 유효성 검사에 실패했습니다.",
                field_errors=field_errors,
            )

    @classmethod
    def create(cls, post_id: int, content: str, author: Author) -> "Comment":
        """신규 댓글 생성 도메인 팩토리"""
        return cls(post_id=post_id, content=content.strip(), author=author)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update_content(self, content: str) -> None:
        if self.is_deleted:
            raise BadRequestException(message="삭제된 댓글은 수정할 수 없습니다.")

        if not content or not content.strip():
            raise ValidationException(
                message="댓글 수정 유효성 검사에 실패했습니다.",
                field_errors={"content": ["댓글 내용은 공백일 수 없습니다."]},
            )

        self.content = content.strip()
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException(message="이미 삭제된 댓글입니다.")
        self.deleted_at = datetime.now(timezone.utc)

    def can_modify_or_delete(self, requester_id: uuid.UUID | None, user_role: Role | None) -> bool:
        return _can_modify(self.author, requester_id, user_role)
# Entities 정의 E
