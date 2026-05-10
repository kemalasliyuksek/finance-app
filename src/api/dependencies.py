"""FastAPI bağımlılıkları - auth ve DB session."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import verify_token
from src.db.session import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """JWT token'dan mevcut kullanıcıyı çıkar.

    Auth endpoint'leri (/me, /change-password, /refresh) için kullanılır.
    Şifre değişikliği zorunluluğunu kontrol etmez.
    """
    try:
        payload = verify_token(credentials.credentials, expected_type="access")
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token",
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token doğrulanamadı",
        )


async def get_current_active_user(
    username: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Aktif ve şifresini değiştirmiş kullanıcı kontrolü.

    Auth dışı tüm endpoint'ler için kullanılır.
    must_change_password == True ise 403 döner.
    """
    from src.db.repositories.user_repo import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_username(username)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı bulunamadı veya devre dışı",
        )

    if user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Devam etmek için şifrenizi değiştirmeniz gerekiyor",
        )

    return username
