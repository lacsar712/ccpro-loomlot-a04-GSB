from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.dye_lot import DyeLot


class RedyeTicket(Base):
    """回修复染单：挂在原染程上，未结案前锁定对应染缸，禁止再开新染程。"""

    __tablename__ = "redye_tickets"
    __table_args__ = (
        # 同一原染程只允许存在一条未结案复染单（closed_at 为空时冲突）
        Index(
            "uq_open_redye_per_lot",
            "dye_lot_id",
            unique=True,
            postgresql_where=text("closed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dye_lot_id: Mapped[int] = mapped_column(ForeignKey("dye_lots.id"), nullable=False, index=True)
    defect_desc: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opener_name: Mapped[str] = mapped_column(String(64), nullable=False)
    closer_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    dye_lot: Mapped["DyeLot"] = relationship("DyeLot", back_populates="redye_tickets")

    @property
    def vat_id(self) -> int:
        """原染程所在染缸，供与染缸列表对账。"""
        return self.dye_lot.vat_id

    @property
    def has_open_redye(self) -> bool:
        return self.closed_at is None
