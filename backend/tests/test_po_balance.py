from decimal import Decimal

from app.services.reconciliation import check_po_remaining_balance
from tests.conftest import make_invoice


def test_within_remaining_balance_passes(db, vendor, po):
    invoice = make_invoice(db, subtotal=Decimal("50000.00"), matched_po_id=po.id)
    result = check_po_remaining_balance(invoice)
    assert result.status == "PASS"


def test_exceeds_remaining_balance_fails_review(db, vendor, partially_consumed_po):
    # PO-1001: total 100000, invoiced 75000 -> remaining 25000. Invoice for 30000 exceeds it.
    invoice = make_invoice(db, subtotal=Decimal("30000.00"))
    invoice.matched_po_id = partially_consumed_po.id
    result = check_po_remaining_balance(invoice)
    assert result.status == "FAIL"
    assert result.severity == "REVIEW"
    assert result.expected == Decimal("25000.00")
    assert result.actual == Decimal("30000.00")


def test_within_configured_tolerance_still_passes(db, vendor, partially_consumed_po):
    # Remaining is 25000; 2% tolerance allows up to 25500.
    invoice = make_invoice(db, subtotal=Decimal("25400.00"))
    invoice.matched_po_id = partially_consumed_po.id
    result = check_po_remaining_balance(invoice)
    assert result.status == "PASS"


def test_falls_back_to_total_when_subtotal_missing(db, vendor, po):
    invoice = make_invoice(db, subtotal=None, total=Decimal("50000.00"))
    invoice.matched_po_id = po.id
    result = check_po_remaining_balance(invoice)
    assert result.status == "PASS"
    assert result.actual == Decimal("50000.00")


def test_no_matched_po_returns_none(db):
    invoice = make_invoice(db)
    assert check_po_remaining_balance(invoice) is None


def test_fully_consumed_po_always_fails(db, vendor, po):
    po.invoiced_amount = po.total_amount
    db.commit()
    invoice = make_invoice(db, subtotal=Decimal("100.00"))
    invoice.matched_po_id = po.id
    result = check_po_remaining_balance(invoice)
    assert result.status == "FAIL"
