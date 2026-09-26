from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Invoice, InvoiceLineItem, POLineItem, PurchaseOrder, Vendor
from app.utils.normalize import normalize_vendor_name


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def vendor(db):
    v = Vendor(
        name="Acme Technologies Pvt Ltd",
        normalized_name=normalize_vendor_name("Acme Technologies Pvt Ltd"),
        tax_id="27AACCA1234F1Z5",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@pytest.fixture()
def other_vendor(db):
    v = Vendor(
        name="Global Office Supplies",
        normalized_name=normalize_vendor_name("Global Office Supplies"),
        tax_id="07AABCG4321H1Z9",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@pytest.fixture()
def po(db, vendor):
    purchase_order = PurchaseOrder(
        po_number="PO-1002",
        vendor_id=vendor.id,
        currency="INR",
        total_amount=Decimal("50000.00"),
        invoiced_amount=Decimal("0.00"),
        status="OPEN",
        created_at=datetime.utcnow(),
    )
    db.add(purchase_order)
    db.commit()
    db.refresh(purchase_order)
    db.add(POLineItem(
        po_id=purchase_order.id, description="Network switch - 24 port",
        quantity=Decimal("2"), unit_price=Decimal("25000.00"), amount=Decimal("50000.00"),
    ))
    db.commit()
    db.refresh(purchase_order)
    return purchase_order


@pytest.fixture()
def partially_consumed_po(db, vendor):
    purchase_order = PurchaseOrder(
        po_number="PO-1001",
        vendor_id=vendor.id,
        currency="INR",
        total_amount=Decimal("100000.00"),
        invoiced_amount=Decimal("75000.00"),
        status="OPEN",
        created_at=datetime.utcnow(),
    )
    db.add(purchase_order)
    db.commit()
    db.refresh(purchase_order)
    db.add(POLineItem(
        po_id=purchase_order.id, description="On-site engineer visits",
        quantity=Decimal("8"), unit_price=Decimal("5000.00"), amount=Decimal("40000.00"),
    ))
    db.commit()
    db.refresh(purchase_order)
    return purchase_order


def make_invoice(db, **overrides) -> Invoice:
    defaults = dict(
        filename="invoice.pdf",
        file_path="/tmp/invoice.pdf",
        status="EXTRACTED",
        invoice_number="INV-1001",
        invoice_date=date(2026, 9, 5),
        vendor_name="Acme Technologies Pvt Ltd",
        vendor_tax_id="27AACCA1234F1Z5",
        currency="INR",
        subtotal=Decimal("50000.00"),
        tax=Decimal("9000.00"),
        total=Decimal("59000.00"),
    )
    defaults.update(overrides)
    invoice = Invoice(**defaults)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def add_line_item(db, invoice: Invoice, **overrides) -> InvoiceLineItem:
    defaults = dict(
        invoice_id=invoice.id,
        description="Network switch - 24 port",
        quantity=Decimal("2"),
        unit_price=Decimal("25000.00"),
        amount=Decimal("50000.00"),
    )
    defaults.update(overrides)
    line = InvoiceLineItem(**defaults)
    db.add(line)
    db.commit()
    return line
