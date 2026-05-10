"""Kimlik doğrulama şemaları."""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    must_change_password: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    username: str
    role: str = "admin"
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Şifre gücü doğrulaması."""
        if len(v) < 8:
            raise ValueError("Şifre en az 8 karakter olmalı")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Şifre en az 1 büyük harf içermeli")
        if not re.search(r"[a-z]", v):
            raise ValueError("Şifre en az 1 küçük harf içermeli")
        if not re.search(r"\d", v):
            raise ValueError("Şifre en az 1 rakam içermeli")
        return v
