import json
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.config import MAX_OCR_PAGES, MIN_EXTRACTABLE_TEXT_CHARS
from app.models import Invoice, InvoiceLineItem
from app.services import pdf_processing
from app.services.audit import log_event
from app.services.llm import get_provider


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def run_extraction(db: Session, invoice: Invoice) -> None:
    try:
        provider = get_provider()
        text = pdf_processing.extract_text(invoice.file_path)
        stripped = text.strip()

        if len(stripped) >= MIN_EXTRACTABLE_TEXT_CHARS:
            log_event(
                db, invoice.id, "PDF_TEXT_EXTRACTED",
                f"Extracted {len(stripped)} characters of native text",
            )
            extracted = provider.extract_from_text(stripped)
            method = "TEXT"
        else:
            images = pdf_processing.render_pages_as_png(invoice.file_path, MAX_OCR_PAGES)
            log_event(
                db, invoice.id, "OCR_USED",
                f"Native text extraction yielded {len(stripped)} characters; "
                f"using vision-based extraction on {len(images)} page(s)",
            )
            extracted = provider.extract_from_images(images)
            method = "OCR_VISION"

        invoice.vendor_name = extracted.vendor_name
        invoice.vendor_tax_id = extracted.vendor_tax_id
        invoice.invoice_number = extracted.invoice_number
        invoice.invoice_date = extracted.invoice_date
        invoice.po_reference = extracted.po_reference
        invoice.currency = extracted.currency
        invoice.subtotal = _to_decimal(extracted.subtotal)
        invoice.tax = _to_decimal(extracted.tax)
        invoice.total = _to_decimal(extracted.total)
        invoice.extraction_method = method
        invoice.extraction_evidence = json.dumps([e.model_dump() for e in extracted.evidence])
        invoice.status = "EXTRACTED"

        for line in extracted.line_items:
            db.add(InvoiceLineItem(
                invoice_id=invoice.id,
                description=line.description,
                quantity=_to_decimal(line.quantity),
                unit_price=_to_decimal(line.unit_price),
                amount=_to_decimal(line.amount),
            ))

        log_event(
            db, invoice.id, "INVOICE_FIELDS_EXTRACTED",
            f"Invoice {extracted.invoice_number or '(no number)'} from "
            f"{extracted.vendor_name or '(unknown vendor)'}, total "
            f"{extracted.total if extracted.total is not None else '(unknown)'} "
            f"{extracted.currency or ''}".strip(),
        )

    except Exception as e:
        db.rollback()
        invoice.status = "EXTRACTION_FAILED"
        log_event(db, invoice.id, "EXTRACTION_FAILED", str(e)[:500])
