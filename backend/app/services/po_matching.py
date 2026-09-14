from decimal import Decimal

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.config import (
    PO_CANDIDATE_DATE_DECAY_DAYS,
    PO_MATCH_HIGH_CONFIDENCE,
    PO_MATCH_REVIEW_THRESHOLD,
    PO_MATCH_WEIGHT_AMOUNT,
    PO_MATCH_WEIGHT_DATE,
    PO_MATCH_WEIGHT_LINE_ITEMS,
    PO_MATCH_WEIGHT_VENDOR,
)
from app.models import Invoice, POMatchCandidate, PurchaseOrder, Vendor


def match_explicit_po(db: Session, invoice: Invoice, vendor: Vendor | None) -> dict:
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == invoice.po_reference).first()

    if not po:
        return {
            "po": None, "confidence": 0.0, "method": "EXPLICIT_REFERENCE_NOT_FOUND",
            "reason": f"Invoice references PO '{invoice.po_reference}', which does not exist.",
        }

    if vendor and po.vendor_id != vendor.id:
        return {
            "po": None, "confidence": 0.0, "method": "EXPLICIT_REFERENCE_VENDOR_MISMATCH",
            "reason": (
                f"PO '{po.po_number}' belongs to vendor '{po.vendor.name}', "
                f"not the matched vendor '{vendor.name}'."
            ),
        }

    return {
        "po": po, "confidence": 100.0, "method": "EXPLICIT_REFERENCE",
        "reason": f"Invoice explicitly references PO '{po.po_number}'.",
    }


def _amount_score(invoice: Invoice, po: PurchaseOrder) -> float:
    invoice_amount = invoice.subtotal if invoice.subtotal is not None else invoice.total
    if invoice_amount is None:
        return 50.0

    remaining = po.total_amount - po.invoiced_amount
    if remaining <= 0:
        return 0.0

    variance_pct = abs(invoice_amount - remaining) / remaining * 100
    return float(max(Decimal("0"), Decimal("100") - variance_pct))


def _line_item_score(invoice: Invoice, po: PurchaseOrder) -> float:
    invoice_lines = [l.description for l in invoice.line_items if l.description]
    po_lines = [l.description for l in po.line_items if l.description]
    if not invoice_lines or not po_lines:
        return 50.0

    scores = [max(fuzz.token_sort_ratio(il, pl) for pl in po_lines) for il in invoice_lines]
    return sum(scores) / len(scores)


def _date_score(invoice: Invoice, po: PurchaseOrder) -> float:
    if not invoice.invoice_date or not po.created_at:
        return 50.0

    days_apart = abs((invoice.invoice_date - po.created_at.date()).days)
    return max(0.0, 100.0 - (days_apart / PO_CANDIDATE_DATE_DECAY_DAYS) * 100.0)


def score_candidates(db: Session, invoice: Invoice, vendor: Vendor | None) -> list[dict]:
    if not vendor:
        return []

    candidates = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.vendor_id == vendor.id, PurchaseOrder.status == "OPEN")
        .all()
    )

    scored = []
    for po in candidates:
        vendor_score = 100.0
        amount_score = _amount_score(invoice, po)
        line_item_score = _line_item_score(invoice, po)
        date_score = _date_score(invoice, po)
        total_score = (
            PO_MATCH_WEIGHT_VENDOR * vendor_score
            + PO_MATCH_WEIGHT_AMOUNT * amount_score
            + PO_MATCH_WEIGHT_LINE_ITEMS * line_item_score
            + PO_MATCH_WEIGHT_DATE * date_score
        )
        scored.append({
            "po": po, "score": total_score, "vendor_score": vendor_score,
            "amount_score": amount_score, "line_item_score": line_item_score, "date_score": date_score,
        })

    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored


def _candidate_reason(candidate: dict) -> str:
    return (
        f"vendor {candidate['vendor_score']:.0f}%, amount {candidate['amount_score']:.0f}%, "
        f"line items {candidate['line_item_score']:.0f}%, date {candidate['date_score']:.0f}% "
        f"-> {candidate['score']:.0f}% overall"
    )


def run_po_matching(db: Session, invoice: Invoice, vendor: Vendor | None) -> dict:
    if invoice.po_reference:
        result = match_explicit_po(db, invoice, vendor)
    else:
        scored = score_candidates(db, invoice, vendor)

        for candidate in scored:
            db.add(POMatchCandidate(
                invoice_id=invoice.id, po_id=candidate["po"].id,
                score=Decimal(str(round(candidate["score"], 2))),
                vendor_score=Decimal(str(round(candidate["vendor_score"], 2))),
                amount_score=Decimal(str(round(candidate["amount_score"], 2))),
                line_item_score=Decimal(str(round(candidate["line_item_score"], 2))),
                date_score=Decimal(str(round(candidate["date_score"], 2))),
                reason=_candidate_reason(candidate),
            ))

        if not scored:
            result = {
                "po": None, "confidence": 0.0, "method": "NO_CANDIDATES",
                "reason": "No open purchase orders found for the matched vendor." if vendor
                else "No vendor matched; cannot search for candidate purchase orders.",
            }
        else:
            best = scored[0]
            if best["score"] >= PO_MATCH_HIGH_CONFIDENCE:
                result = {
                    "po": best["po"], "confidence": round(best["score"], 2), "method": "CANDIDATE_HIGH_CONFIDENCE",
                    "reason": f"Best candidate PO '{best['po'].po_number}': {_candidate_reason(best)}.",
                }
            elif best["score"] >= PO_MATCH_REVIEW_THRESHOLD:
                result = {
                    "po": None, "confidence": round(best["score"], 2), "method": "CANDIDATE_NEEDS_REVIEW",
                    "reason": (
                        f"Best candidate PO '{best['po'].po_number}' scored {best['score']:.0f}%, "
                        f"below the auto-match threshold ({PO_MATCH_HIGH_CONFIDENCE:.0f}%); needs manual review."
                    ),
                }
            else:
                result = {
                    "po": None, "confidence": round(best["score"], 2), "method": "CANDIDATE_LOW_CONFIDENCE",
                    "reason": f"Best candidate PO '{best['po'].po_number}' scored only {best['score']:.0f}%; no confident match.",
                }

    invoice.matched_po_id = result["po"].id if result["po"] else None
    invoice.po_match_confidence = result["confidence"]
    invoice.po_match_method = result["method"]
    invoice.po_match_reason = result["reason"]
    return result
