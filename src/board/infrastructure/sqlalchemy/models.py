import uuid

from sqlalchemy import UUID, BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.core.models import Base, DateTimeBase


class BoardModel(Base, DateTimeBase):
    """게시판 설정 테이블"""
    __tablename__ = "boards"

    board_id: Mapped[str] = mapped_column("id", String(30), primary_key=True)
    board_name: Mapped[str] = mapped_column(String(100), nullable=False)
    page_size: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # 게시판 권한 (작성 권한은 회원 이상만)
    edit_role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)
    view_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    list_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    comment_list_role: Mapped[str] = mapped_column(String(20), default="ALL", nullable=False)
    comment_edit_role: Mapped[str] = mapped_column(String(20), default="USER", nullable=False)


class PostModel(Base, DateTimeBase):
    """게시글 테이블"""
    __tablename__ = "posts"

    __table_args__ = (
        Index("ix_posts_id_deleted_at", "id", "deleted_at"),
        Index("ix_posts_author_id", "author_id"),
    )

    post_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    board_id: Mapped[str] = mapped_column(String(30), ForeignKey("boards.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 작성 시점의 회원 이름 (목록에서 조인 없이 표시)
    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 회원만 작성 가능 → NOT NULL. 회원은 소프트 삭제하므로 실제 행 삭제는 RESTRICT로 막음
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    board: Mapped["BoardModel"] = relationship("BoardModel", lazy="joined")


class CommentModel(Base, DateTimeBase):
    """댓글 테이블"""
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_post_id_deleted_at", "post_id", "deleted_at"),
    )

    comment_id: Mapped[int] = mapped_column("id", BigInteger, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("posts.id"), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    author_name: Mapped[str] = mapped_column(String(50), nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    post: Mapped[PostModel] = relationship("PostModel")
