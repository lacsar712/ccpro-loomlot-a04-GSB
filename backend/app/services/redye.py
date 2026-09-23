"""回修复染单的共享状态查询。

未结案复染的判定在全项目只此一处：
- 染程开立拦截
- 染程列表 / 染缸列表的「挂未结案复染」标记
- 看板未结案复染计数
均复用下面的查询，保证三处口径一致，不允许各算各的。
"""

from typing import Iterable, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.dye_lot import DyeLot
from app.models.fastness_check import FastnessCheck
from app.models.redye_ticket import RedyeTicket


def _open_query(db: Session):
    return db.query(RedyeTicket).filter(RedyeTicket.closed_at.is_(None))


def open_ticket_lot_ids(db: Session, lot_ids: Optional[Iterable[int]] = None) -> Set[int]:
    """挂着未结案复染单的原染程 id 集合。"""
    q = _open_query(db)
    if lot_ids is not None:
        ids = list(lot_ids)
        if not ids:
            return set()
        q = q.filter(RedyeTicket.dye_lot_id.in_(ids))
    return {row[0] for row in q.with_entities(RedyeTicket.dye_lot_id).all()}


def open_ticket_vat_ids(db: Session, vat_ids: Optional[Iterable[int]] = None) -> Set[int]:
    """存在未结案复染单的染缸 id 集合（经原染程归属染缸）。"""
    q = (
        db.query(DyeLot.vat_id)
        .join(RedyeTicket, RedyeTicket.dye_lot_id == DyeLot.id)
        .filter(RedyeTicket.closed_at.is_(None))
    )
    if vat_ids is not None:
        ids = list(vat_ids)
        if not ids:
            return set()
        q = q.filter(DyeLot.vat_id.in_(ids))
    return {row[0] for row in q.distinct().all()}


def vat_has_open_ticket(db: Session, vat_id: int) -> bool:
    return vat_id in open_ticket_vat_ids(db, [vat_id])


def lot_has_open_ticket(db: Session, lot_id: int) -> bool:
    return _open_query(db).filter(RedyeTicket.dye_lot_id == lot_id).first() is not None


def count_open_tickets(db: Session) -> int:
    """看板与列表共用的未结案复染条数（= 未结案原染程数，亦 = 被锁染缸去重口径外的单数）。"""
    return _open_query(db).with_entities(func.count(RedyeTicket.id)).scalar() or 0


def evaluate_closure(db: Session, lot: DyeLot) -> Tuple[bool, str]:
    """结案双检条件：原染程至少两条色牢度，且最新一条耐洗等级不低于上一条。

    时间相同时以 id 作为确定性次序。
    """
    checks = (
        db.query(FastnessCheck)
        .filter(FastnessCheck.dye_lot_id == lot.id)
        .order_by(FastnessCheck.checked_at.asc(), FastnessCheck.id.asc())
        .all()
    )
    if len(checks) < 2:
        return False, "原染程色牢度抽检不足两条，双检未通过，不可结案"
    older, newer = checks[-2], checks[-1]
    if newer.wash_fastness < older.wash_fastness:
        return (
            False,
            f"最新耐洗等级 {newer.wash_fastness} 级低于上一条 {older.wash_fastness} 级，双检未通过，不可结案",
        )
    return True, ""
