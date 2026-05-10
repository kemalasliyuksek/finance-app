"""Emir endpoint'leri."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.constants import OrderStatus
from src.db.repositories.order_repo import OrderRepository
from src.db.session import get_db
from src.schemas.order import OrderRead
from src.schemas.pagination import PaginatedResponse

router = APIRouter(tags=["orders"])


@router.get("", response_model=PaginatedResponse[OrderRead])
async def list_orders(
    status_filter: OrderStatus | None = Query(None, alias="status"),
    symbol: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None, pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> PaginatedResponse[OrderRead]:
    """Filtrelenebilir emir listesi."""
    repo = OrderRepository(db)
    orders, total = await repo.get_filtered(
        status=status_filter, symbol=symbol, limit=limit, offset=offset,
        sort_by=sort_by, sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[OrderRead.model_validate(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> OrderRead:
    """Tekil emir detayı."""
    repo = OrderRepository(db)
    order = await repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emir bulunamadı")
    return OrderRead.model_validate(order)
