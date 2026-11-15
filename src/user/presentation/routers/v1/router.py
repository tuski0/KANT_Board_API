from typing import Annotated

from fastapi import APIRouter, Depends, status

from shared.core.schemas import APIResponse
from user.application.service import UserService
from user.domain.user import User
from user.presentation.dependencies import get_current_user, provide_user_service
from user.presentation.schemas import ChangePasswordRequest, SignUpUserRequest, UserResponse

router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post(
    "",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="회원가입",
    description="새로운 사용자를 등록합니다. 비밀번호는 bcrypt로 해싱하여 저장합니다.",
    responses={
        409: {"model": APIResponse[None], "description": "이미 사용 중인 이메일"},
        422: {"model": APIResponse[None], "description": "입력값 검증 실패"},
    },
)
async def sign_up(
    request: SignUpUserRequest,
    user_service: Annotated[UserService, Depends(provide_user_service)],
):
    user = await user_service.register_user(
        email=request.email,
        name=request.name,
        password=request.password,
    )
    return APIResponse.ok(data=UserResponse.model_validate(user), message="회원가입이 완료되었습니다.")


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="내 정보 조회 (로그인 필요)",
    responses={401: {"model": APIResponse[None], "description": "로그인 필요"}},
)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return APIResponse.ok(data=UserResponse.model_validate(current_user))


@router.patch(
    "/me/password",
    response_model=APIResponse[None],
    summary="내 비밀번호 변경 (로그인 필요)",
    responses={
        400: {"model": APIResponse[None], "description": "기존 비밀번호 불일치 등"},
        401: {"model": APIResponse[None], "description": "로그인 필요"},
    },
)
async def change_my_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(provide_user_service)],
):
    await user_service.change_password(
        user_id=current_user.id,
        old_password=request.old_password,
        new_password=request.new_password,
    )
    return APIResponse.ok(message="비밀번호가 성공적으로 변경되었습니다.")


@router.delete(
    "/me",
    response_model=APIResponse[None],
    summary="회원 탈퇴 (로그인 필요, 소프트 삭제)",
    responses={401: {"model": APIResponse[None], "description": "로그인 필요"}},
)
async def withdraw_me(
    current_user: Annotated[User, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(provide_user_service)],
):
    await user_service.withdraw(target_user_id=current_user.id, requester=current_user)
    return APIResponse.ok(message="회원 탈퇴가 완료되었습니다.")
