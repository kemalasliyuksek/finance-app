"""Kimlik doğrulama endpoint'leri."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from src.api.dependencies import get_current_user
from src.api.middleware.rate_limit import limiter
from src.config import settings
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_db
from src.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse, UserInfo

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Kullanıcı girişi - JWT access + refresh token döner."""
    repo = UserRepository(db)
    user = await repo.get_by_username(body.username)

    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre",
        )

    access_token = create_access_token(user.username)
    refresh_token = create_refresh_token(user.username)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        must_change_password=user.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest | None = None,
    response: Response = None,  # type: ignore[assignment]
) -> TokenResponse:
    """Refresh token ile yeni access token al."""
    token = body.refresh_token if body else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token gerekli",
        )

    try:
        payload = verify_token(token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz refresh token",
        )

    username = payload.get("sub")
    access_token = create_access_token(username)
    new_refresh = create_refresh_token(username)

    if response:
        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=settings.jwt_refresh_token_expire_days * 86400,
            path="/api/v1/auth",
        )

    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.get("/me", response_model=UserInfo)
async def me(
    username: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserInfo:
    """Mevcut kullanıcı bilgisi (must_change_password flag'i dahil)."""
    repo = UserRepository(db)
    user = await repo.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı",
        )
    return UserInfo(
        username=user.username,
        role=user.role,
        must_change_password=user.must_change_password,
    )


@router.post("/change-password")
@limiter.limit("3/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    username: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Şifre değiştir."""
    repo = UserRepository(db)
    user = await repo.get_by_username(username)

    if not user or not verify_password(body.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre yanlış",
        )

    new_hash = hash_password(body.new_password)
    await repo.update_password(username, new_hash)

    # Zorunlu şifre değiştirme flag'ini kaldır
    if user.must_change_password:
        await repo.update_must_change_password(username, False)

    return {"message": "Şifre başarıyla değiştirildi"}
