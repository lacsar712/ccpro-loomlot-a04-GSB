"""回修复染对账：未结案复染状态的唯一数据源。

染缸开立拦截、染程/染缸列表的「挂未结案复染」标记、看板未结案条数，
全部经由本模块的同一条未结案查询派生，不允许各处自行另算。
"""

from typing import Iterable, Optional, Set

from sqlalchemy.orm import Session

from app.models.dye_lot import DyeLot
from app.models.rework_ticket import ReworkTicket


def open_tickets_query(db: Session):
    """所有未结案复染单（closed_at 为空）。"""
    return db.query(ReworkTicket).filter(ReworkTicket.closed_at.is_(None))


def open_lot_ids(db: Session, lot_ids: Optional[Iterable[int]] = None) -> Set[int]:
    """挂着未结案复染单的原染程 id 集合。"""
    q = open_tickets_query(db).with_entities(ReworkTicket.dye_lot_id)
    if lot_ids is not None:
        lot_ids = list(lot_ids)
        if not lot_ids:
            return set()
        q = q.filter(ReworkTicket.dye_lot_id.in_(lot_ids))
    return {row[0] for row in q.all()}


def open_vat_ids(db: Session, vat_ids: Optional[Iterable[int]] = None) -> Set[int]:
    """存在未结案复染单的染缸 id 集合（复染单经原染程定位染缸）。"""
    q = (
        open_tickets_query(db)
        .join(DyeLot, ReworkTicket.dye_lot_id == DyeLot.id)
        .with_entities(DyeLot.vat_id)
    )
    if vat_ids is not None:
        vat_ids = list(vat_ids)
        if not vat_ids:
            return set()
        q = q.filter(DyeLot.vat_id.in_(vat_ids))
    return {row[0] for row in q.all()}


def open_count(db: Session) -> int:
    """未结案复染单总条数，看板与列表共用。"""
    return open_tickets_query(db).count()


def annotate_lots(db: Session, lots: list) -> list:
    """给染程实例回填 has_open_rework（直接挂实例属性，供 schema 读取）。"""
    flagged = open_lot_ids(db, [lot.id for lot in lots])
    for lot in lots:
        lot.has_open_rework = lot.id in flagged
    return lots


def annotate_vats(db: Session, vats: list) -> list:
    """给染缸实例回填 has_open_rework。"""
    flagged = open_vat_ids(db, [vat.id for vat in vats])
    for vat in vats:
        vat.has_open_rework = vat.id in flagged
    return vats
