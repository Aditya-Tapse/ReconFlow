from app.services.duplicate_detection import check_duplicate
from tests.conftest import make_invoice


def test_no_duplicate_when_no_prior_invoices(db):
    invoice = make_invoice(db)
    result = check_duplicate(db, invoice)
    assert result.status == "PASS"


def test_skipped_when_vendor_name_missing(db):
    invoice = make_invoice(db, vendor_name=None)
    result = check_duplicate(db, invoice)
    assert result.status == "SKIPPED"


def test_strong_duplicate_same_vendor_and_invoice_number_is_blocking(db):
    make_invoice(db, invoice_number="INV-1001")
    invoice = make_invoice(db, invoice_number="INV-1001", filename="rescanned.pdf")
    result = check_duplicate(db, invoice)
    assert result.status == "FAIL"
    assert result.severity == "BLOCKING"
    assert "duplicate" in result.message.lower()


def test_duplicate_detection_ignores_file_identity(db):
    make_invoice(db, invoice_number="INV-1001", filename="original.pdf", file_path="/uploads/a.pdf")
    invoice = make_invoice(
        db, invoice_number="INV-1001", filename="rescanned_copy.pdf", file_path="/uploads/b.pdf",
    )
    result = check_duplicate(db, invoice)
    assert result.status == "FAIL"
    assert result.severity == "BLOCKING"


def test_possible_duplicate_same_vendor_date_total_is_review(db):
    make_invoice(db, invoice_number="INV-1001")
    invoice = make_invoice(db, invoice_number="INV-9999")
    result = check_duplicate(db, invoice)
    assert result.status == "FAIL"
    assert result.severity == "REVIEW"


def test_different_vendor_same_invoice_number_is_not_duplicate(db):
    make_invoice(db, invoice_number="INV-1001", vendor_name="Global Office Supplies")
    invoice = make_invoice(db, invoice_number="INV-1001")
    result = check_duplicate(db, invoice)
    assert result.status == "PASS"
