from sqlalchemy.orm import Session

from app.models import AuditEvent


def log_event(db: Session, invoice_id: int, event_type: str, message: str = None) -> AuditEvent:
    event = AuditEvent(invoice_id=invoice_id, event_type=event_type, message=message)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
