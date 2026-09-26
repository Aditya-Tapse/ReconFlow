from decimal import Decimal

from app.models import ValidationResult
from app.services.decision_engine import run_decision
from tests.conftest import add_line_item, make_invoice


def test_happy_path_is_approved(db, vendor, po):
    invoice = make_invoice(
        db, status="VALIDATED", matched_vendor_id=vendor.id, matched_po_id=po.id,
        currency="INR", subtotal=Decimal("50000.00"),
    )
    add_line_item(db, invoice)

    decision = run_decision(db, invoice)

    assert decision.decision == "APPROVED"
    assert invoice.status == "APPROVED"


def test_prior_blocking_failure_rejects(db, vendor, po):
    invoice = make_invoice(
        db, status="VALIDATED", matched_vendor_id=vendor.id, matched_po_id=po.id,
        currency="INR", subtotal=Decimal("50000.00"),
    )
    add_line_item(db, invoice)
    db.add(ValidationResult(
        invoice_id=invoice.id, rule_id="DUPLICATE_CHECK", status="FAIL", severity="BLOCKING",
        message="Same vendor and invoice number as invoice #1 - duplicate invoice.",
    ))
    db.commit()

    decision = run_decision(db, invoice)

    assert decision.decision == "REJECTED"
    assert "duplicate" in decision.reason.lower()
    assert invoice.status == "REJECTED"


def test_prior_review_failure_without_blocking_is_manual_review(db, vendor, po):
    invoice = make_invoice(
        db, status="VALIDATED", matched_vendor_id=vendor.id, matched_po_id=po.id,
        currency="INR", subtotal=Decimal("50000.00"),
    )
    add_line_item(db, invoice)
    db.add(ValidationResult(
        invoice_id=invoice.id, rule_id="REQUIRED_FIELD_INVOICE_DATE", status="FAIL", severity="REVIEW",
        message="Invoice date is missing from the extracted invoice.",
    ))
    db.commit()

    decision = run_decision(db, invoice)

    assert decision.decision == "MANUAL_REVIEW"
    assert invoice.status == "MANUAL_REVIEW"


def test_blocking_takes_priority_over_review(db, vendor, po):
    invoice = make_invoice(
        db, status="VALIDATED", matched_vendor_id=vendor.id, matched_po_id=po.id,
        currency="USD",  # will produce a BLOCKING currency mismatch against the INR PO
        subtotal=Decimal("50000.00"),
    )
    add_line_item(db, invoice)
    db.add(ValidationResult(
        invoice_id=invoice.id, rule_id="REQUIRED_FIELD_INVOICE_DATE", status="FAIL", severity="REVIEW",
        message="Invoice date is missing.",
    ))
    db.commit()

    decision = run_decision(db, invoice)

    assert decision.decision == "REJECTED"
    assert "currency" in decision.reason.lower()


def test_amount_over_remaining_balance_is_manual_review(db, vendor, partially_consumed_po):
    invoice = make_invoice(
        db, status="VALIDATED", matched_vendor_id=vendor.id, matched_po_id=partially_consumed_po.id,
        currency="INR", subtotal=Decimal("30000.00"),
    )
    add_line_item(db, invoice, description="On-site engineer visits", quantity=Decimal("6"),
                  unit_price=Decimal("5000.00"), amount=Decimal("30000.00"))

    decision = run_decision(db, invoice)

    assert decision.decision == "MANUAL_REVIEW"
    assert "remaining balance" in decision.reason.lower()


def test_does_nothing_if_invoice_not_yet_validated(db):
    invoice = make_invoice(db, status="EXTRACTED")
    decision = run_decision(db, invoice)
    assert decision is None
    assert invoice.status == "EXTRACTED"
