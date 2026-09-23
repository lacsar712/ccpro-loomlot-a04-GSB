from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.dye_lot import DyeLot
    from app.models.user import User


class ReworkTicket(Base):
    """回修复染单：挂在原染程上，结案前冻结所在染缸的新染程开立。"""

    __tablename__ = "rework_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dye_lot_id: Mapped[int] = mapped_column(ForeignKey("dye_lots.id"), nullable=False, index=True)
    defect_note: Mapped[str] = mapped_column(Text, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    opener_name: Mapped[str] = mapped_column(String(64), nullable=False)

    dye_lot: Mapped["DyeLot"] = relationship("DyeLot", back_populates="rework_tickets")
