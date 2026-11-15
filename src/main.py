import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.security import HTTPBearer

from shared.core.database import AsyncSessionLocal, close_db, engine
from shared.core.exception_handlers import register_exception_handlers
from shared.core.logger import get_logger
from shared.core.models import Base, init_models
from wiring import wire_dependencies

from auth.presentation.routers.v1.router import router as auth_router
from board.presentation.routers.v1.router import router as board_router
from user.presentation.routers.v1.router import router as user_router

logger = get_logger("app.main")


async def seed_initial_data() -> None:
    """기본 게시판(free)과 관리자 계정 준비 (이미 있으면 건너뜀)"""
    from board.application.service import BoardService
    from board.infrastructure.sqlalchemy.board_repository import SqlAlchemyBoardRepository
    from user.application.service import UserService
    from user.infrastructure.repositories import SqlAlchemyUserRepository
    from wiring.user import password_hasher

    async with AsyncSessionLocal() as session:
        board_repo = SqlAlchemyBoardRepository(session)
        if not await board_repo.exists_by_id("free"):
            await BoardService(board_repo).create_board(board_id="free", board_name="자유게시판")
            logger.info("기본 게시판 'free'를 생성했습니다.")

        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")
        if admin_email and admin_password:
            user_service = UserService(SqlAlchemyUserRepository(session), password_hasher)
            await user_service.create_admin_if_absent(admin_email, "관리자", admin_password)
            logger.info("관리자 계정을 확인했습니다: %s", admin_email)

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("애플리케이션 시작, 모델 초기화 및 DB 스키마 확인 중...")
    init_models()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await seed_initial_data()

    logger.info("애플리케이션 준비 완료.")
    yield

    logger.info("애플리케이션 종료 처리 중...")
    await close_db()


app = FastAPI(
    title="KANT 게시판 API",
    description=(
        "FastAPI + PostgreSQL(SQLAlchemy) + JWT 기반 RESTful 게시판 API\n\n"
        "- 글·댓글 작성은 **로그인한 회원만** 가능합니다.\n"
        "- 수정·삭제는 **작성자 본인 또는 관리자**만 가능합니다.\n"
        "- 로그인 후 받은 `access_token`을 오른쪽 위 **Authorize** 버튼에 입력하세요."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# 전역 예외 핸들러 바인딩
register_exception_handlers(app)

# 의존성 주입 일괄 바인딩
wire_dependencies(app)

# 라우터 등록
# 토큰 검증은 wiring 의 dependency_overrides 로 주입되어 Swagger 문서에 드러나지 않음.
# 라우터에 Bearer 스키마를 명시해서 Swagger 의 Authorize 토큰이 모든 API 요청에 붙도록 함.
bearer_scheme = HTTPBearer(auto_error=False)
app.include_router(user_router, dependencies=[Depends(bearer_scheme)])
app.include_router(auth_router)
app.include_router(board_router, dependencies=[Depends(bearer_scheme)])


@app.get("/health", tags=["Health"], summary="서버 상태 확인")
async def health():
    return {"status": "ok"}
