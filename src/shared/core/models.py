from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# 데이터베이스 테이블의 기준(베이스 클래스) 정의
class Base(DeclarativeBase):
    pass


class DateTimeBase:
    # default 에 함수 자체(utc_now)를 넘겨야 행을 추가할 때마다 현재 시각이 들어감
    # (datetime.now() 를 바로 넘기면 서버 시작 시각 하나로 고정됨)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, onupdate=utc_now, nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )


# 모델 초기화
def init_models():
    """SQLAlchemy 모델 메타데이터 등록"""
    import user.infrastructure.models  # 회원
    import auth.infrastructure.models  # 토큰 블랙리스트
    import board.infrastructure.sqlalchemy.models  # 게시판
