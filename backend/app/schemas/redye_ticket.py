from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RedyeTicketCreate(BaseModel):
    dye_lot_id: int = Field(..., alias="dyeLotId")
    defect_desc: str = Field(..., min_length=8, alias="defectDesc")

    model_config = ConfigDict(populate_by_name=True)


class RedyeTicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    dye_lot_id: int = Field(serialization_alias="dyeLotId")
    vat_id: int = Field(serialization_alias="vatId")
    defect_desc: str = Field(serialization_alias="defectDesc")
    opened_at: datetime = Field(serialization_alias="openedAt")
    closed_at: Optional[datetime] = Field(default=None, serialization_alias="closedAt")
    opener_name: str = Field(serialization_alias="openerName")
    closer_name: Optional[str] = Field(default=None, serialization_alias="closerName")

    # 列表行直接带出「是否挂未结案复染」，与染缸/染程列表共用同一口径
    has_open_redye: bool = Field(default=False, serialization_alias="hasOpenRedye")
