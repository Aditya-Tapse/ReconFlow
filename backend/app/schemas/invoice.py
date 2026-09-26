from datetime import date, datetime
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


class InvoiceLineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class EvidenceItemOut(BaseModel):
    field: str
    value: Optional[str] = None
    source_text: Optional[str] = None


class MatchedVendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tax_id: Optional[str] = None


class MatchedPOOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_number: str
    currency: str
    total_amount: float
    invoiced_amount: float
    status: str


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    status: str
    extraction_method: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    po_reference: Optional[str] = None
    currency: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    created_at: datetime
    line_items: list[InvoiceLineItemOut] = []

    matched_vendor_id: Optional[int] = None
    vendor_match_confidence: Optional[float] = None
    vendor_match_method: Optional[str] = None
    vendor_match_reason: Optional[str] = None
    matched_vendor: Optional[MatchedVendorOut] = None

    matched_po_id: Optional[int] = None
    po_match_confidence: Optional[float] = None
    po_match_method: Optional[str] = None
    po_match_reason: Optional[str] = None
    matched_po: Optional[MatchedPOOut] = None
