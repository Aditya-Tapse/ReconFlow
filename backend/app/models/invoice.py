from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)

    invoice_number = Column(String, nullable=True, index=True)
    invoice_date = Column(Date, nullable=True)
    vendor_name = Column(String, nullable=True)
    vendor_tax_id = Column(String, nullable=True)
    po_reference = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    subtotal = Column(Numeric(14, 2), nullable=True)
    tax = Column(Numeric(14, 2), nullable=True)
    total = Column(Numeric(14, 2), nullable=True)

    status = Column(String, default="PROCESSING", index=True)
    extraction_method = Column(String, nullable=True)
    extraction_evidence = Column(Text, nullable=True)
    matched_vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    vendor_match_confidence = Column(Numeric(5, 2), nullable=True)
    vendor_match_method = Column(String, nullable=True)
    vendor_match_reason = Column(String, nullable=True)

    matched_po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=True)
    po_match_confidence = Column(Numeric(5, 2), nullable=True)
    po_match_method = Column(String, nullable=True)
    po_match_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    line_items = relationship("InvoiceLineItem", back_populates="invoice")
    audit_events = relationship("AuditEvent", back_populates="invoice")
    validation_results = relationship("ValidationResult", back_populates="invoice")
    decision = relationship("Decision", back_populates="invoice", uselist=False)


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=True)
    quantity = Column(Numeric(12, 2), nullable=True)
    unit_price = Column(Numeric(14, 2), nullable=True)
    amount = Column(Numeric(14, 2), nullable=True)

    invoice = relationship("Invoice", back_populates="line_items")
