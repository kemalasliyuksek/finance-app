"""Sinyal endpoint'leri."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_active_user
from src.api.middleware.rate_limit import limiter
from src.constants import SignalStatus
from src.core.audit import log_audit
from src.core.events import publish
from src.db.repositories.signal_repo import SignalRepository
from src.db.session import get_db
from src.schemas.pagination import PaginatedResponse
from src.schemas.signal import SignalDetailRead, SignalRead, TimelineEvent

router = APIRouter(tags=["signals"])


@router.get("", response_model=PaginatedResponse[SignalRead])
async def list_signals(
    status_filter: SignalStatus | None = Query(None, alias="status"),
    symbol: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None, pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> PaginatedResponse[SignalRead]:
    """Filtrelenebilir sinyal listesi."""
    repo = SignalRepository(db)
    signals, total = await repo.get_filtered(
        status=status_filter, symbol=symbol, limit=limit, offset=offset,
        sort_by=sort_by, sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[SignalRead.model_validate(s) for s in signals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{signal_id}", response_model=SignalRead)
async def get_signal(
    signal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> SignalRead:
    """Tekil sinyal detayı."""
    repo = SignalRepository(db)
    signal = await repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinyal bulunamadı")
    return SignalRead.model_validate(signal)


@router.get("/{signal_id}/detail", response_model=SignalDetailRead)
async def get_signal_detail(
    signal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> SignalDetailRead:
    """Sinyal detayı — ilişkili order, trade ve timeline ile birlikte."""
    import sqlalchemy as sa
    from src.models.audit_log import AuditLog
    from src.models.order import Order
    from src.models.trade import Trade
    from src.schemas.order import OrderRead

    repo = SignalRepository(db)
    signal = await repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinyal bulunamadı")

    # İlişkili order
    order_stmt = sa.select(Order).where(Order.signal_id == signal_id).limit(1)
    order_result = await db.execute(order_stmt)
    order = order_result.scalars().first()

    # İlişkili trade (order üzerinden)
    trade = None
    if order:
        trade_stmt = sa.select(Trade).where(Trade.entry_order_id == order.id).limit(1)
        trade_result = await db.execute(trade_stmt)
        trade = trade_result.scalars().first()

    # Audit log timeline — sinyal + order + trade kayıtları
    signal_id_str = str(signal_id)
    entity_ids = [signal_id_str]
    if order:
        entity_ids.append(str(order.id))
    if trade:
        entity_ids.append(str(trade.id))

    audit_stmt = (
        sa.select(AuditLog)
        .where(AuditLog.entity_id.in_(entity_ids))
        .order_by(AuditLog.created_at.asc())
    )
    audit_result = await db.execute(audit_stmt)
    audit_logs = audit_result.scalars().all()

    # Timeline oluştur — sinyal oluşturma + audit kayıtları
    timeline = [
        TimelineEvent(
            action="signal_created",
            timestamp=signal.created_at,
            user="system",
            details={"symbol": signal.symbol, "side": signal.side, "confidence": float(signal.confidence)},
        )
    ]
    for log in audit_logs:
        timeline.append(TimelineEvent(
            action=log.action,
            timestamp=log.created_at,
            user=log.user,
            details=log.changes,
        ))

    return SignalDetailRead(
        signal=SignalRead.model_validate(signal),
        order=OrderRead.model_validate(order).model_dump() if order else None,
        trade={
            "id": str(trade.id),
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": float(trade.entry_price),
            "exit_price": float(trade.exit_price) if trade.exit_price else None,
            "quantity": float(trade.quantity),
            "realized_pnl": float(trade.realized_pnl) if trade.realized_pnl else None,
            "status": trade.status,
            "opened_at": str(trade.opened_at),
            "closed_at": str(trade.closed_at) if trade.closed_at else None,
        } if trade else None,
        timeline=timeline,
    )


@router.post("/{signal_id}/approve", response_model=SignalRead)
@limiter.limit("10/minute")
async def approve_signal(
    request: Request,
    signal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> SignalRead:
    """Sinyali onayla."""
    repo = SignalRepository(db)
    signal = await repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinyal bulunamadı")
    if signal.status != SignalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sinyal onaylanamaz")

    updated = await repo.update_status(signal_id, SignalStatus.APPROVED, approved_by=_user, expected_status=SignalStatus.PENDING)
    if not updated:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sinyal durumu değişmiş, onaylanamadı")
    await log_audit(
        db, action="approve", entity_type="signal",
        entity_id=str(signal_id), user=_user,
        changes={"status": "approved", "symbol": signal.symbol, "side": signal.side},
    )

    # Execution worker'a bildir (signal:approved event)
    await publish(
        "signal:approved",
        {
            "signal_id": str(signal_id),
            "symbol": signal.symbol,
            "side": signal.side,
            "entry_price": float(signal.entry_price),
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "take_profit": float(signal.take_profit) if signal.take_profit else None,
            "confidence": float(signal.confidence),
        },
    )

    await db.refresh(signal)
    return SignalRead.model_validate(signal)


@router.post("/{signal_id}/reject", response_model=SignalRead)
@limiter.limit("10/minute")
async def reject_signal(
    request: Request,
    signal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_active_user),
) -> SignalRead:
    """Sinyali reddet."""
    repo = SignalRepository(db)
    signal = await repo.get_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sinyal bulunamadı")
    if signal.status != SignalStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sinyal reddedilemez")

    updated = await repo.update_status(signal_id, SignalStatus.REJECTED, approved_by=_user, expected_status=SignalStatus.PENDING)
    if not updated:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Sinyal durumu değişmiş, reddedilemedi")
    await log_audit(
        db, action="reject", entity_type="signal",
        entity_id=str(signal_id), user=_user,
        changes={"status": "rejected", "symbol": signal.symbol, "side": signal.side},
    )
    await db.refresh(signal)
    return SignalRead.model_validate(signal)
