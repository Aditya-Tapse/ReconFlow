import json

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Invoice, POMatchCandidate
from app.schemas.invoice import (
    InvoiceCreateResponse,
    InvoiceOut,
    AuditEventOut,
    EvidenceItemOut,
)
from app.schemas.validation import POMatchCandidateOut, ValidationResultOut
from app.services.audit import log_event
from app.services.invoice_extraction import run_extraction
from app.services.invoice_processing import run_processing
from app.utils.storage import save_upload

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

ALLOWED_CONTENT_TYPES = {"application/pdf"}


@router.post("", response_model=InvoiceCreateResponse)
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    file_path = save_upload(file.filename, content)

    invoice = Invoice(filename=file.filename, file_path=file_path, status="PROCESSING")
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    log_event(db, invoice.id, "INVOICE_RECEIVED", f"Received file {file.filename}")

    run_extraction(db, invoice)
    run_processing(db, invoice)

    return InvoiceCreateResponse(invoice_id=f"INV_CASE_{invoice.id}", status=invoice.status)


@router.get("", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).order_by(Invoice.created_at.desc()).all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/{invoice_id}/audit-trail", response_model=list[AuditEventOut])
def get_audit_trail(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice.audit_events


@router.get("/{invoice_id}/evidence", response_model=list[EvidenceItemOut])
def get_evidence(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not invoice.extraction_evidence:
        return []
    return json.loads(invoice.extraction_evidence)


@router.get("/{invoice_id}/validation-results", response_model=list[ValidationResultOut])
def get_validation_results(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice.validation_results


@router.get("/{invoice_id}/po-candidates", response_model=list[POMatchCandidateOut])
def get_po_candidates(invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return (
        db.query(POMatchCandidate)
        .filter(POMatchCandidate.invoice_id == invoice_id)
        .order_by(POMatchCandidate.score.desc())
        .all()
    )
