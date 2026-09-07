from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    normalized_name = Column(String, nullable=False, index=True)
    tax_id = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    po_number = Column(String, unique=True, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    currency = Column(String, nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    invoiced_amount = Column(Numeric(14, 2), default=0)
    status = Column(String, default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("Vendor", back_populates="purchase_orders")
    line_items = relationship("POLineItem", back_populates="purchase_order")


class POLineItem(Base):
    __tablename__ = "po_line_items"

    id = Column(Integer, primary_key=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)

    purchase_order = relationship("PurchaseOrder", back_populates="line_items")
