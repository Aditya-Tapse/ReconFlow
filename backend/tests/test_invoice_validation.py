from decimal import Decimal

from app.services.validation import check_arithmetic, check_required_fields
from tests.conftest import add_line_item, make_invoice


def test_required_fields_all_present_pass(db):
    invoice = make_invoice(db)
    results = check_required_fields(invoice)
    assert all(r.status == "PASS" for r in results)


def test_required_field_missing_invoice_number_fails_review(db):
    invoice = make_invoice(db, invoice_number=None)
    results = {r.rule_id: r for r in check_required_fields(invoice)}
    result = results["REQUIRED_FIELD_INVOICE_NUMBER"]
    assert result.status == "FAIL"
    assert result.severity == "REVIEW"


def test_required_field_blank_string_counts_as_missing(db):
    invoice = make_invoice(db, vendor_name="   ")
    results = {r.rule_id: r for r in check_required_fields(invoice)}
    assert results["REQUIRED_FIELD_VENDOR_NAME"].status == "FAIL"


def test_arithmetic_line_total_matches_passes(db):
    invoice = make_invoice(db)
    add_line_item(db, invoice)
    results = [r for r in check_arithmetic(invoice) if r.rule_id == "ARITHMETIC_LINE_TOTAL"]
    assert results[0].status == "PASS"


def test_arithmetic_line_total_mismatch_fails(db):
    invoice = make_invoice(db)
    add_line_item(db, invoice, amount=Decimal("45000.00"))
    results = [r for r in check_arithmetic(invoice) if r.rule_id == "ARITHMETIC_LINE_TOTAL"]
    assert results[0].status == "FAIL"
    assert results[0].severity == "REVIEW"


def test_arithmetic_within_rounding_tolerance_passes(db):
    invoice = make_invoice(db, subtotal=Decimal("50000.50"))
    add_line_item(db, invoice)
    results = [r for r in check_arithmetic(invoice) if r.rule_id == "ARITHMETIC_SUBTOTAL"]
    assert results[0].status == "PASS"


def test_arithmetic_subtotal_plus_tax_mismatch_fails(db):
    invoice = make_invoice(db, subtotal=Decimal("50000.00"), tax=Decimal("9000.00"), total=Decimal("60000.00"))
    results = [r for r in check_arithmetic(invoice) if r.rule_id == "ARITHMETIC_TOTAL"]
    assert results[0].status == "FAIL"
