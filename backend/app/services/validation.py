from decimal import Decimal

from sqlalchemy.orm import Session

from app.config import ARITHMETIC_ROUNDING_TOLERANCE
from app.models import Invoice, ValidationResult

TOLERANCE = Decimal(str(ARITHMETIC_ROUNDING_TOLERANCE))

REQUIRED_FIELDS = {
    "invoice_number": "Invoice number",
    "invoice_date": "Invoice date",
    "vendor_name": "Vendor",
    "total": "Total",
    "currency": "Currency",
}


def _result(invoice_id: int, rule_id: str, status: str, severity: str | None, message: str,
            expected=None, actual=None) -> ValidationResult:
    return ValidationResult(
        invoice_id=invoice_id, rule_id=rule_id, status=status, severity=severity,
        expected=expected, actual=actual, message=message,
    )


def check_required_fields(invoice: Invoice) -> list[ValidationResult]:
    results = []
    for field, label in REQUIRED_FIELDS.items():
        value = getattr(invoice, field)
        missing = value is None or (isinstance(value, str) and not value.strip())
        if missing:
            results.append(_result(
                invoice.id, f"REQUIRED_FIELD_{field.upper()}", "FAIL", "REVIEW",
                f"{label} is missing from the extracted invoice.",
            ))
        else:
            results.append(_result(
                invoice.id, f"REQUIRED_FIELD_{field.upper()}", "PASS", None,
                f"{label} is present.",
            ))
    return results


def check_arithmetic(invoice: Invoice) -> list[ValidationResult]:
    results = []

    for line in invoice.line_items:
        if line.quantity is None or line.unit_price is None or line.amount is None:
            continue
        expected = (line.quantity * line.unit_price).quantize(Decimal("0.01"))
        status = "PASS" if abs(expected - line.amount) <= TOLERANCE else "FAIL"
        results.append(_result(
            invoice.id, "ARITHMETIC_LINE_TOTAL", status, "REVIEW" if status == "FAIL" else None,
            f"Line '{line.description}': quantity x unit price = {expected}, stated amount = {line.amount}.",
            expected=expected, actual=line.amount,
        ))

    priced_lines = [l.amount for l in invoice.line_items if l.amount is not None]
    if priced_lines and invoice.subtotal is not None:
        expected_subtotal = sum(priced_lines)
        status = "PASS" if abs(expected_subtotal - invoice.subtotal) <= TOLERANCE else "FAIL"
        results.append(_result(
            invoice.id, "ARITHMETIC_SUBTOTAL", status, "REVIEW" if status == "FAIL" else None,
            f"Sum of line items = {expected_subtotal}, stated subtotal = {invoice.subtotal}.",
            expected=expected_subtotal, actual=invoice.subtotal,
        ))

    if invoice.subtotal is not None and invoice.tax is not None and invoice.total is not None:
        expected_total = invoice.subtotal + invoice.tax
        status = "PASS" if abs(expected_total - invoice.total) <= TOLERANCE else "FAIL"
        results.append(_result(
            invoice.id, "ARITHMETIC_TOTAL", status, "REVIEW" if status == "FAIL" else None,
            f"Subtotal + tax = {expected_total}, stated total = {invoice.total}.",
            expected=expected_total, actual=invoice.total,
        ))

    return results


def run_validation(db: Session, invoice: Invoice) -> list[ValidationResult]:
    results = check_required_fields(invoice) + check_arithmetic(invoice)
    for result in results:
        db.add(result)
    return results
