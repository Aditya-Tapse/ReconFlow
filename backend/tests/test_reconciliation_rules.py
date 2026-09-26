from app.services.reconciliation import check_currency_match, check_po_match, check_vendor_match
from tests.conftest import make_invoice


def test_vendor_match_passes_when_matched(db, vendor):
    invoice = make_invoice(db, matched_vendor_id=vendor.id)
    result = check_vendor_match(invoice)
    assert result.status == "PASS"


def test_vendor_match_blocking_when_unmatched(db):
    invoice = make_invoice(db, matched_vendor_id=None)
    result = check_vendor_match(invoice)
    assert result.status == "FAIL"
    assert result.severity == "BLOCKING"


def test_po_match_passes_when_matched(db, po):
    invoice = make_invoice(db, matched_po_id=po.id)
    result = check_po_match(invoice)
    assert result.status == "PASS"


def test_po_match_review_when_unmatched(db):
    invoice = make_invoice(db, matched_po_id=None, po_match_reason="No candidates scored.")
    result = check_po_match(invoice)
    assert result.status == "FAIL"
    assert result.severity == "REVIEW"
    assert result.message == "No candidates scored."


def test_currency_match_passes_when_equal(db, po):
    invoice = make_invoice(db, matched_po_id=po.id, currency="INR")
    result = check_currency_match(invoice)
    assert result.status == "PASS"


def test_currency_mismatch_is_blocking(db, po):
    invoice = make_invoice(db, matched_po_id=po.id, currency="USD")
    result = check_currency_match(invoice)
    assert result.status == "FAIL"
    assert result.severity == "BLOCKING"


def test_currency_match_none_when_no_matched_po(db):
    invoice = make_invoice(db, matched_po_id=None)
    assert check_currency_match(invoice) is None
