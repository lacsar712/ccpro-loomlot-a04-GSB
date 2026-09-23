from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReworkTicketCreate(BaseModel):
    dye_lot_id: int = Field(..., alias="dyeLotId")
    defect_note: str = Field(..., min_length=8, alias="defectNote")
    opened_at: datetime = Field(..., alias="openedAt")

    model_config = ConfigDict(populate_by_name=True)


class ReworkTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    dye_lot_id: int = Field(serialization_alias="dyeLotId")
    defect_note: str = Field(serialization_alias="defectNote")
    opened_at: datetime = Field(serialization_alias="openedAt")
    closed_at: Optional[datetime] = Field(None, serialization_alias="closedAt")
    opener_name: str = Field(serialization_alias="openerName")
