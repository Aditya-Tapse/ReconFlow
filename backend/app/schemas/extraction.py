from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

PRIORITY_EVIDENCE_FIELDS = [
    "invoice_number",
    "vendor_name",
    "po_reference",
    "invoice_date",
    "total",
    "tax",
    "currency",
]


class EvidenceItem(BaseModel):
    field: str = Field(description="Name of the extracted field this evidence supports")
    value: Optional[str] = Field(default=None, description="The extracted value, as a string")
    source_text: Optional[str] = Field(
        default=None, description="The exact text in the document that this value was read from"
    )


class ExtractedLineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class ExtractedInvoice(BaseModel):
    vendor_name: Optional[str] = None
    vendor_tax_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    po_reference: Optional[str] = None
    currency: Optional[str] = None
    line_items: list[ExtractedLineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description=f"One entry per priority field found in the document: {PRIORITY_EVIDENCE_FIELDS}",
    )
