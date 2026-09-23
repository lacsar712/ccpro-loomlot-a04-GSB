from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck
from app.models.rework_ticket import ReworkTicket
from app.models.user import User
from app.schemas.rework_ticket import ReworkTicketCreate, ReworkTicketOut
from app.services import rework as rework_service

router = APIRouter(prefix="/api/rework-tickets", tags=["rework-tickets"])


def require_supervisor(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅染坊主管可结案复染单")


@router.get("", response_model=List[ReworkTicketOut])
def list_tickets(
    dye_lot_id: Optional[int] = Query(None, alias="dyeLotId"),
    open_only: bool = Query(False, alias="openOnly"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ReworkTicket)
    if dye_lot_id is not None:
        q = q.filter(ReworkTicket.dye_lot_id == dye_lot_id)
    if open_only:
        q = q.filter(ReworkTicket.closed_at.is_(None))
    return q.order_by(ReworkTicket.id.desc()).all()


@router.post("", response_model=ReworkTicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: ReworkTicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lot = db.query(DyeLot).filter(DyeLot.id == payload.dye_lot_id).first()
    if not lot:
        raise HTTPException(status_code=400, detail="原染程不存在")
    # 同一原染程未结案时不可再开
    if (
        db.query(ReworkTicket.id)
        .filter(
            ReworkTicket.dye_lot_id == payload.dye_lot_id,
            ReworkTicket.closed_at.is_(None),
        )
        .first()
        is not None
    ):
        raise HTTPException(status_code=409, detail="该原染程已有未结案复染单，不可重复开单")
    item = ReworkTicket(
        dye_lot_id=payload.dye_lot_id,
        defect_note=payload.defect_note,
        opened_at=payload.opened_at,
        closed_at=None,
        opener_name=current_user.display_name,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{ticket_id}/close", response_model=ReworkTicketOut)
def close_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_supervisor(current_user)
    ticket = db.query(ReworkTicket).filter(ReworkTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="复染单不存在")
    if ticket.closed_at is not None:
        raise HTTPException(status_code=400, detail="该复染单已结案")

    # 双检色牢度：原染程上至少两条，且较新一条耐洗等级不低于较旧一条
    checks = (
        db.query(FastnessCheck)
        .filter(FastnessCheck.dye_lot_id == ticket.dye_lot_id)
        .order_by(FastnessCheck.checked_at.asc(), FastnessCheck.id.asc())
        .all()
    )
    if len(checks) < 2:
        raise HTTPException(status_code=400, detail="原染程色牢度抽检不足两条，无法结案")
    older, newer = checks[-2], checks[-1]
    if newer.wash_fastness < older.wash_fastness:
        raise HTTPException(
            status_code=400,
            detail=(
                f"较新一条耐洗等级 {newer.wash_fastness} 低于较旧一条 {older.wash_fastness}，"
                "复检未达标，无法结案"
            ),
        )

    ticket.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ticket)
    return ticket
