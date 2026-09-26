import itertools
from datetime import date, datetime
from decimal import Decimal

from app.models import POLineItem, PurchaseOrder
from app.services.po_matching import match_explicit_po, run_po_matching
from app.services.vendor_matching import match_vendor
from tests.conftest import add_line_item, make_invoice


def test_explicit_po_reference_found_and_vendor_matches(db, vendor, po):
    invoice = make_invoice(db, po_reference=po.po_number)
    result = match_explicit_po(db, invoice, vendor)
    assert result["po"].id == po.id
    assert result["method"] == "EXPLICIT_REFERENCE"
    assert result["confidence"] == 100.0


def test_explicit_po_reference_not_found(db, vendor):
    invoice = make_invoice(db, po_reference="PO-9999")
    result = match_explicit_po(db, invoice, vendor)
    assert result["po"] is None
    assert result["method"] == "EXPLICIT_REFERENCE_NOT_FOUND"


def test_explicit_po_reference_belonging_to_different_vendor_is_refused(db, vendor, other_vendor, po):
    invoice = make_invoice(db, po_reference=po.po_number, vendor_name=other_vendor.name)
    result = match_explicit_po(db, invoice, other_vendor)
    assert result["po"] is None
    assert result["method"] == "EXPLICIT_REFERENCE_VENDOR_MISMATCH"


_po_counter = itertools.count(1)


def _po_dated(db, vendor, *, created_at, total_amount, invoiced_amount, description, quantity, unit_price):
    purchase_order = PurchaseOrder(
        po_number=f"PO-TEST-{next(_po_counter)}", vendor_id=vendor.id, currency="INR",
        total_amount=total_amount, invoiced_amount=invoiced_amount, status="OPEN", created_at=created_at,
    )
    db.add(purchase_order)
    db.commit()
    db.refresh(purchase_order)
    db.add(POLineItem(
        po_id=purchase_order.id, description=description, quantity=quantity,
        unit_price=unit_price, amount=quantity * unit_price,
    ))
    db.commit()
    db.refresh(purchase_order)
    return purchase_order


def test_candidate_scoring_high_confidence_auto_matches(db, vendor):
    good = _po_dated(
        db, vendor, created_at=datetime(2026, 9, 5), total_amount=Decimal("50000.00"),
        invoiced_amount=Decimal("0.00"), description="Network switch - 24 port",
        quantity=Decimal("2"), unit_price=Decimal("25000.00"),
    )
    invoice = make_invoice(db, po_reference=None, invoice_date=date(2026, 9, 5))
    add_line_item(db, invoice)

    result = run_po_matching(db, invoice, vendor)
    assert result["po"].id == good.id
    assert result["method"] == "CANDIDATE_HIGH_CONFIDENCE"
    assert result["confidence"] >= 90


def test_candidate_scoring_prefers_the_po_with_the_matching_balance(db, vendor):
    _po_dated(
        db, vendor, created_at=datetime(2026, 9, 5), total_amount=Decimal("25000.00"),
        invoiced_amount=Decimal("0.00"), description="On-site engineer visits",
        quantity=Decimal("1"), unit_price=Decimal("25000.00"),
    )
    good = _po_dated(
        db, vendor, created_at=datetime(2026, 9, 5), total_amount=Decimal("50000.00"),
        invoiced_amount=Decimal("0.00"), description="Network switch - 24 port",
        quantity=Decimal("2"), unit_price=Decimal("25000.00"),
    )
    invoice = make_invoice(db, po_reference=None, invoice_date=date(2026, 9, 5))
    add_line_item(db, invoice)

    result = run_po_matching(db, invoice, vendor)
    assert result["po"].id == good.id


def test_candidate_scoring_low_confidence_leaves_unmatched(db, vendor):
    _po_dated(
        db, vendor, created_at=datetime(2020, 1, 1), total_amount=Decimal("999999.00"),
        invoiced_amount=Decimal("0.00"), description="Completely unrelated bulk cement order",
        quantity=Decimal("500"), unit_price=Decimal("1999.98"),
    )
    invoice = make_invoice(db, po_reference=None, invoice_date=date(2026, 9, 5))
    add_line_item(db, invoice)

    result = run_po_matching(db, invoice, vendor)
    assert result["po"] is None
    assert result["method"] in ("CANDIDATE_NEEDS_REVIEW", "CANDIDATE_LOW_CONFIDENCE")


def test_no_candidates_when_vendor_has_no_open_pos(db, other_vendor):
    invoice = make_invoice(db, po_reference=None, vendor_name=other_vendor.name)
    result = run_po_matching(db, invoice, other_vendor)
    assert result["po"] is None
    assert result["method"] == "NO_CANDIDATES"


def test_no_candidates_when_no_vendor_matched(db):
    invoice = make_invoice(db, po_reference=None, vendor_name=None, vendor_tax_id=None)
    result = run_po_matching(db, invoice, None)
    assert result["po"] is None
    assert result["method"] == "NO_CANDIDATES"


def test_end_to_end_vendor_then_po_matching(db, vendor, po):
    invoice = make_invoice(db, po_reference=po.po_number)
    vendor_result = match_vendor(db, invoice)
    po_result = run_po_matching(db, invoice, vendor_result["vendor"])
    assert po_result["po"].id == po.id
