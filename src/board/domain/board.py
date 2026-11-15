import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from board.domain.enums import Role
from shared.core.exceptions import BadRequestException, ValidationException

"""
1. 게시판은 무한대로 생성 가능하다. 게시판 설정 하나가 게시판 하나가 된다.
2. 글·댓글 작성은 회원만 가능하다. (비회원 작성 미지원)
   - 목록/상세/댓글 목록 열람 권한은 ALL(비회원 포함)로 열어둘 수 있다.
   - 글쓰기/댓글쓰기 권한은 최소 USER 이상이어야 한다.
3. 권한은 다음과 같다.
    - 게시글 수정 가능 권한(edit_role): 글 쓰기, 글 수정, 글 삭제 가능
    - 게시글 상세 보기 가능 권한(view_role): 글 상세 열람 가능
    - 게시글 목록 보기 가능 권한(list_role): 글 목록 열람 가능
    - 댓글 목록 보기 가능 권한(comment_list_role): 댓글 목록 열람 가능
    - 댓글 수정 가능 권한(comment_edit_role): 댓글 쓰기, 댓글 수정, 댓글 삭제 권한
4. 게시글 목록에서 노출될 게시글 갯수는 설정 가능해야 하며 기본값은 20이다.
5. 게시판 ID는 영문 소문자로 시작, 영문 소문자/숫자/하이픈/언더스코어 허용 (2~30자)
6. 게시판 설정은 소프트 삭제를 하며 삭제된 게시판은 수정할 수 없다.
"""

BOARD_ID_REGEX = re.compile(r"^[a-z][a-z0-9_-]{1,29}$")


@dataclass(frozen=True)
class Authority:
    """게시판 세부 권한 설정"""
    edit_role: Role = Role.USER
    view_role: Role = Role.ALL
    list_role: Role = Role.ALL
    comment_list_role: Role = Role.ALL
    comment_edit_role: Role = Role.USER

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}
        # 비회원 작성을 지원하지 않으므로 작성 권한에 ALL 금지
        if Role(self.edit_role) == Role.ALL:
            field_errors.setdefault("edit_role", []).append("글쓰기 권한은 USER 또는 ADMIN 이어야 합니다.")
        if Role(self.comment_edit_role) == Role.ALL:
            field_errors.setdefault("comment_edit_role", []).append("댓글쓰기 권한은 USER 또는 ADMIN 이어야 합니다.")
        if field_errors:
            raise ValidationException(
                message="게시판 권한 설정이 올바르지 않습니다.",
                field_errors=field_errors,
            )

    def can_edit(self, user_role: Role | str | None) -> bool:
        return self._check(user_role, self.edit_role)

    def can_view(self, user_role: Role | str | None) -> bool:
        return self._check(user_role, self.view_role)

    def can_list(self, user_role: Role | str | None) -> bool:
        return self._check(user_role, self.list_role)

    def can_view_comments(self, user_role: Role | str | None) -> bool:
        return self._check(user_role, self.comment_list_role)

    def can_edit_comments(self, user_role: Role | str | None) -> bool:
        return self._check(user_role, self.comment_edit_role)

    def _check(self, user_role: Role | str | None, required: Role) -> bool:
        if user_role is None:  # 비회원
            return required == Role.ALL

        if isinstance(user_role, str):
            user_role = Role(user_role)

        return user_role.satisfies(required)


@dataclass
class Board:
    """게시판 설정 엔티티"""
    board_id: str  # free, notice
    board_name: str  # 자유게시판, 공지사항
    authority: Authority = field(default_factory=Authority)
    page_size: int = 20

    created_at: datetime | None = None
    modified_at: datetime | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        field_errors: dict[str, list[str]] = {}

        if not self.board_id:
            field_errors.setdefault("board_id", []).append("게시판 ID는 필수 입력값입니다.")
        else:
            normalized_id = self.board_id.strip().lower()
            if not BOARD_ID_REGEX.match(normalized_id):
                field_errors.setdefault("board_id", []).append(
                    f"유효하지 않은 게시판 ID 형식입니다 ('{self.board_id}'). "
                    "영문 소문자로 시작해야 하며, 2~30자의 영문 소문자, 숫자, 특수문자(-, _)만 사용할 수 있습니다."
                )
            else:
                self.board_id = normalized_id

        if not self.board_name or not self.board_name.strip():
            field_errors.setdefault("board_name", []).append("게시판 이름은 공백일 수 없습니다.")

        if self.page_size < 1:
            field_errors.setdefault("page_size", []).append("게시글 목록 노출 개수는 1 이상이어야 합니다.")

        if field_errors:
            raise ValidationException(
                message="게시판 설정 유효성 검사에 실패했습니다.",
                field_errors=field_errors,
            )

    @classmethod
    def create(
        cls,
        board_id: str,
        board_name: str,
        authority: Authority | None = None,
        page_size: int = 20,
    ) -> "Board":
        """게시판 생성"""
        return cls(
            board_id=board_id,
            board_name=board_name,
            authority=authority or Authority(),
            page_size=page_size,
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update_config(
        self,
        board_name: str,
        page_size: int,
        authority: Authority | None = None,
    ) -> None:
        if self.is_deleted:
            raise BadRequestException(message="삭제된 게시판 설정은 수정할 수 없습니다.")

        field_errors: dict[str, list[str]] = {}
        if not board_name or not board_name.strip():
            field_errors.setdefault("board_name", []).append("게시판 이름은 공백일 수 없습니다.")

        if page_size < 1:
            field_errors.setdefault("page_size", []).append("게시글 목록 노출 개수는 1 이상이어야 합니다.")

        if field_errors:
            raise ValidationException(
                message="게시판 설정 수정 유효성 검사에 실패했습니다.",
                field_errors=field_errors,
            )

        self.board_name = board_name.strip()
        self.page_size = page_size
        if authority is not None:
            self.authority = authority
        self.modified_at = datetime.now(timezone.utc)

    def delete(self) -> None:
        if self.is_deleted:
            raise BadRequestException(message="이미 삭제된 게시판입니다.")
        self.deleted_at = datetime.now(timezone.utc)
