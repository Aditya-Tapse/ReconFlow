from sqlalchemy.orm import Session

from app.models import Invoice, ValidationResult
from app.utils.normalize import normalize_vendor_name


def check_duplicate(db: Session, invoice: Invoice) -> ValidationResult:
    result = _evaluate_duplicate(db, invoice)
    db.add(result)
    return result


def _evaluate_duplicate(db: Session, invoice: Invoice) -> ValidationResult:
    if not invoice.vendor_name:
        return ValidationResult(
            invoice_id=invoice.id, rule_id="DUPLICATE_CHECK", status="SKIPPED", severity=None,
            message="No vendor name extracted; duplicate check skipped.",
        )

    normalized = normalize_vendor_name(invoice.vendor_name)
    others = (
        db.query(Invoice)
        .filter(Invoice.id != invoice.id, Invoice.vendor_name.isnot(None))
        .all()
    )
    same_vendor = [o for o in others if normalize_vendor_name(o.vendor_name) == normalized]

    if invoice.invoice_number:
        for other in same_vendor:
            if other.invoice_number and other.invoice_number.strip().lower() == invoice.invoice_number.strip().lower():
                return ValidationResult(
                    invoice_id=invoice.id, rule_id="DUPLICATE_CHECK", status="FAIL", severity="BLOCKING",
                    message=(
                        f"Same vendor and invoice number as invoice #{other.id} "
                        f"({other.filename}) - duplicate invoice."
                    ),
                )

    if invoice.invoice_date and invoice.total is not None:
        for other in same_vendor:
            if other.invoice_date == invoice.invoice_date and other.total == invoice.total:
                return ValidationResult(
                    invoice_id=invoice.id, rule_id="DUPLICATE_CHECK", status="FAIL", severity="REVIEW",
                    message=(
                        f"Same vendor, invoice date, and total as invoice #{other.id} "
                        f"({other.filename}) - possible duplicate."
                    ),
                )

    return ValidationResult(
        invoice_id=invoice.id, rule_id="DUPLICATE_CHECK", status="PASS", severity=None,
        message="No matching prior invoice found.",
    )
