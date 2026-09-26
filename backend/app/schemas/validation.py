from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ValidationResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_id: str
    status: str
    severity: Optional[str] = None
    expected: Optional[float] = None
    actual: Optional[float] = None
    variance_pct: Optional[float] = None
    allowed_variance_pct: Optional[float] = None
    message: Optional[str] = None
    created_at: datetime


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision: str
    reason: Optional[str] = None
    created_at: datetime


class POMatchCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    po_id: int
    score: float
    vendor_score: Optional[float] = None
    amount_score: Optional[float] = None
    line_item_score: Optional[float] = None
    date_score: Optional[float] = None
    reason: Optional[str] = None
