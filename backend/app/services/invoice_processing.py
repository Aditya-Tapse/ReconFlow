from sqlalchemy.orm import Session

from app.models import Invoice, ValidationResult
from app.services.audit import log_event
from app.services.duplicate_detection import check_duplicate
from app.services.po_matching import run_po_matching
from app.services.validation import run_validation
from app.services.vendor_matching import run_vendor_matching


def _validation_summary(results: list[ValidationResult]) -> str:
    failed = [r.rule_id for r in results if r.status == "FAIL"]
    if not failed:
        return f"All {len(results)} validation checks passed."
    return f"{len(failed)} of {len(results)} checks failed: {', '.join(failed)}."


def run_processing(db: Session, invoice: Invoice) -> None:
    if invoice.status != "EXTRACTED":
        return

    try:
        results = run_validation(db, invoice)
        results.append(check_duplicate(db, invoice))
        log_event(db, invoice.id, "VALIDATION_COMPLETED", _validation_summary(results))

        vendor_result = run_vendor_matching(db, invoice)
        log_event(
            db, invoice.id,
            "VENDOR_MATCHED" if vendor_result["vendor"] else "VENDOR_NOT_MATCHED",
            vendor_result["reason"],
        )

        po_result = run_po_matching(db, invoice, vendor_result["vendor"])
        log_event(
            db, invoice.id,
            "PO_MATCHED" if po_result["po"] else "PO_NOT_MATCHED",
            po_result["reason"],
        )

        invoice.status = "VALIDATED"
        db.commit()

    except Exception as e:
        db.rollback()
        invoice.status = "PROCESSING_FAILED"
        log_event(db, invoice.id, "PROCESSING_FAILED", str(e)[:500])
