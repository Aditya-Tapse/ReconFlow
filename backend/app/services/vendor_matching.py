from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.config import VENDOR_FUZZY_MATCH_THRESHOLD
from app.models import Invoice, Vendor
from app.utils.normalize import normalize_vendor_name


def match_vendor(db: Session, invoice: Invoice) -> dict:
    if invoice.vendor_tax_id:
        vendor = db.query(Vendor).filter(Vendor.tax_id == invoice.vendor_tax_id).first()
        if vendor:
            return {
                "vendor": vendor, "confidence": 100.0, "method": "TAX_ID",
                "reason": f"Exact match on tax ID '{invoice.vendor_tax_id}' to vendor '{vendor.name}'.",
            }

    if not invoice.vendor_name:
        return {
            "vendor": None, "confidence": 0.0, "method": "NONE",
            "reason": "No vendor name or tax ID was extracted from the invoice.",
        }

    normalized = normalize_vendor_name(invoice.vendor_name)

    vendor = db.query(Vendor).filter(Vendor.normalized_name == normalized).first()
    if vendor:
        return {
            "vendor": vendor, "confidence": 100.0, "method": "NORMALIZED_NAME",
            "reason": f"Exact match on normalized vendor name '{normalized}' to vendor '{vendor.name}'.",
        }

    best_vendor, best_score = None, 0.0
    for candidate in db.query(Vendor).all():
        score = fuzz.token_sort_ratio(normalized, candidate.normalized_name)
        if score > best_score:
            best_vendor, best_score = candidate, score

    if best_vendor and best_score >= VENDOR_FUZZY_MATCH_THRESHOLD:
        return {
            "vendor": best_vendor, "confidence": round(best_score, 2), "method": "FUZZY_NAME",
            "reason": f"Fuzzy match to vendor '{best_vendor.name}' ({best_score:.0f}% name similarity).",
        }

    return {
        "vendor": None, "confidence": round(best_score, 2), "method": "NONE",
        "reason": f"No vendor matched with sufficient confidence (best fuzzy match {best_score:.0f}%).",
    }


def run_vendor_matching(db: Session, invoice: Invoice) -> dict:
    result = match_vendor(db, invoice)
    invoice.matched_vendor_id = result["vendor"].id if result["vendor"] else None
    invoice.vendor_match_confidence = result["confidence"]
    invoice.vendor_match_method = result["method"]
    invoice.vendor_match_reason = result["reason"]
    return result
