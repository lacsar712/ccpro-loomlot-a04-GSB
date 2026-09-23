from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user, require_admin
from app.database import get_db
from app.models.dye_lot import DyeLot
from app.models.redye_ticket import RedyeTicket
from app.models.user import User
from app.schemas.redye_ticket import RedyeTicketCreate, RedyeTicketOut
from app.services import redye

router = APIRouter(prefix="/api/redye-tickets", tags=["redye-tickets"])


@router.get("", response_model=List[RedyeTicketOut])
def list_tickets(
    dye_lot_id: Optional[int] = Query(None, alias="dyeLotId"),
    vat_id: Optional[int] = Query(None, alias="vatId"),
    open_only: bool = Query(False, alias="open"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(RedyeTicket)
    if dye_lot_id is not None:
        q = q.filter(RedyeTicket.dye_lot_id == dye_lot_id)
    if vat_id is not None:
        q = q.join(DyeLot, DyeLot.id == RedyeTicket.dye_lot_id).filter(DyeLot.vat_id == vat_id)
    if open_only:
        q = q.filter(RedyeTicket.closed_at.is_(None))
    return (
        q.options(selectinload(RedyeTicket.dye_lot))
        .order_by(RedyeTicket.id.desc())
        .all()
    )


@router.post("", response_model=RedyeTicketOut, status_code=status.HTTP_201_CREATED)
def open_ticket(
    payload: RedyeTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """操作员即可开单；开单时刻由服务端记录，开单人取当前登录用户。"""
    lot = db.query(DyeLot).filter(DyeLot.id == payload.dye_lot_id).first()
    if not lot:
        raise HTTPException(status_code=400, detail="原染程不存在")
    if redye.lot_has_open_ticket(db, lot.id):
        raise HTTPException(status_code=409, detail="该原染程已有未结案复染单，不可重复开立")

    now = datetime.now(timezone.utc)
    item = RedyeTicket(
        dye_lot_id=payload.dye_lot_id,
        defect_desc=payload.defect_desc,
        opened_at=now,
        closed_at=None,
        opener_name=current_user.display_name,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该原染程已有未结案复染单，不可重复开立")
    db.refresh(item)
    return item


@router.post("/{ticket_id}/close", response_model=RedyeTicketOut)
def close_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """结案仅主管；双检色牢度达标方可结案，否则 400。"""
    item = db.query(RedyeTicket).filter(RedyeTicket.id == ticket_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="复染单不存在")
    if item.closed_at is not None:
        raise HTTPException(status_code=400, detail="复染单已结案")

    lot = db.query(DyeLot).filter(DyeLot.id == item.dye_lot_id).first()
    ok, reason = redye.evaluate_closure(db, lot)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)

    item.closed_at = datetime.now(timezone.utc)
    item.closer_name = current_user.display_name
    db.commit()
    db.refresh(item)
    return item


@router.get("/{ticket_id}", response_model=RedyeTicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    item = db.query(RedyeTicket).filter(RedyeTicket.id == ticket_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="复染单不存在")
    return item
