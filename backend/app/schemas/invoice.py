from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InvoiceCreateResponse(BaseModel):
    invoice_id: str
    status: str


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    message: Optional[str] = None
    created_at: datetime


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    total: Optional[float] = None
    created_at: datetime
