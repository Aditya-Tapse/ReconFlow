from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    severity = Column(String, nullable=True)
    expected = Column(Numeric(14, 2), nullable=True)
    actual = Column(Numeric(14, 2), nullable=True)
    variance_pct = Column(Numeric(6, 2), nullable=True)
    allowed_variance_pct = Column(Numeric(6, 2), nullable=True)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="validation_results")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), unique=True, nullable=False)
    decision = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="decision")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    event_type = Column(String, nullable=False)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="audit_events")
