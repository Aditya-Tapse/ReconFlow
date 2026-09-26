from sqlalchemy.orm import Session

from app.models import Decision, Invoice, ValidationResult
from app.services.audit import log_event
from app.services.reconciliation import run_reconciliation


def _build_reason(blocking: list[ValidationResult], review: list[ValidationResult]) -> str:
    if blocking:
        return " | ".join(r.message for r in blocking if r.message)
    if review:
        return " | ".join(r.message for r in review if r.message)
    return "All validation, matching, and reconciliation checks passed."


def run_decision(db: Session, invoice: Invoice) -> Decision | None:
    if invoice.status != "VALIDATED":
        return None

    try:
        prior_results = db.query(ValidationResult).filter(ValidationResult.invoice_id == invoice.id).all()
        reconciliation_results = run_reconciliation(db, invoice)
        all_results = prior_results + reconciliation_results

        failed = [r for r in all_results if r.status == "FAIL"]
        blocking = [r for r in failed if r.severity == "BLOCKING"]
        review = [r for r in failed if r.severity == "REVIEW"]

        if blocking:
            decision_value = "REJECTED"
        elif review:
            decision_value = "MANUAL_REVIEW"
        else:
            decision_value = "APPROVED"

        reason = _build_reason(blocking, review)

        decision = Decision(invoice_id=invoice.id, decision=decision_value, reason=reason[:2000])
        db.add(decision)
        invoice.status = decision_value
        db.commit()

        log_event(db, invoice.id, "DECISION_CREATED", f"{decision_value}: {reason[:300]}")
        return decision

    except Exception as e:
        db.rollback()
        invoice.status = "DECISION_FAILED"
        log_event(db, invoice.id, "DECISION_FAILED", str(e)[:500])
        return None
