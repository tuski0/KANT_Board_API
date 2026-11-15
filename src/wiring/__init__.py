from fastapi import FastAPI

from wiring.auth import wire_auth_dependencies
from wiring.board import wire_board_dependencies
from wiring.user import wire_user_dependencies


# FastAPI Dependency Overrides 와이어링
# presentation/dependencies.py 의 provide_* 함수를 실제 구현(SQLAlchemy 저장소, 서비스)으로 연결
def wire_dependencies(app: FastAPI) -> None:
    wire_user_dependencies(app)
    wire_auth_dependencies(app)
    wire_board_dependencies(app)
