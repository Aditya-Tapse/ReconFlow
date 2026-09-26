from decimal import Decimal

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.config import LINE_ITEM_MATCH_THRESHOLD, PO_AMOUNT_TOLERANCE_PCT, UNIT_PRICE_TOLERANCE_PCT
from app.models import Invoice, ValidationResult


def _result(invoice_id: int, rule_id: str, status: str, severity: str | None, message: str,
            expected=None, actual=None, variance_pct=None, allowed_variance_pct=None) -> ValidationResult:
    return ValidationResult(
        invoice_id=invoice_id, rule_id=rule_id, status=status, severity=severity, message=message,
        expected=expected, actual=actual, variance_pct=variance_pct, allowed_variance_pct=allowed_variance_pct,
    )


def check_vendor_match(invoice: Invoice) -> ValidationResult:
    if not invoice.matched_vendor_id:
        return _result(
            invoice.id, "VENDOR_MATCH", "FAIL", "BLOCKING",
            "No vendor could be confidently matched to this invoice.",
        )
    return _result(
        invoice.id, "VENDOR_MATCH", "PASS", None,
        f"Invoice vendor matched to '{invoice.matched_vendor.name}'.",
    )


def check_po_match(invoice: Invoice) -> ValidationResult:
    if not invoice.matched_po_id:
        return _result(
            invoice.id, "PO_MATCH", "FAIL", "REVIEW",
            invoice.po_match_reason or "No purchase order could be confidently matched.",
        )
    return _result(
        invoice.id, "PO_MATCH", "PASS", None,
        f"Invoice matched to purchase order '{invoice.matched_po.po_number}'.",
    )


def check_currency_match(invoice: Invoice) -> ValidationResult | None:
    if not invoice.matched_po_id:
        return None

    po = invoice.matched_po
    if not invoice.currency or not po.currency:
        return _result(
            invoice.id, "CURRENCY_MATCH", "FAIL", "REVIEW",
            "Invoice or PO currency is missing; cannot verify currency match.",
        )
    if invoice.currency.strip().upper() != po.currency.strip().upper():
        return _result(
            invoice.id, "CURRENCY_MATCH", "FAIL", "BLOCKING",
            f"Invoice currency '{invoice.currency}' does not match PO '{po.po_number}' currency '{po.currency}'.",
        )
    return _result(
        invoice.id, "CURRENCY_MATCH", "PASS", None,
        f"Invoice and PO currency both '{invoice.currency}'.",
    )


def check_po_remaining_balance(invoice: Invoice) -> ValidationResult | None:
    if not invoice.matched_po_id:
        return None

    po = invoice.matched_po
    invoice_amount = invoice.subtotal if invoice.subtotal is not None else invoice.total
    if invoice_amount is None:
        return _result(
            invoice.id, "PO_AMOUNT_TOLERANCE", "FAIL", "REVIEW",
            "Invoice has no subtotal or total; cannot compare against the PO's remaining balance.",
        )

    remaining = po.total_amount - po.invoiced_amount
    allowed = Decimal(str(PO_AMOUNT_TOLERANCE_PCT))
    variance_pct = (
        Decimal("100") if remaining <= 0
        else (invoice_amount - remaining) / remaining * 100
    )

    if variance_pct <= allowed:
        return _result(
            invoice.id, "PO_AMOUNT_TOLERANCE", "PASS", None,
            f"Invoice amount {invoice_amount} is within PO '{po.po_number}''s remaining balance of {remaining}.",
            expected=remaining, actual=invoice_amount, variance_pct=variance_pct, allowed_variance_pct=allowed,
        )

    return _result(
        invoice.id, "PO_AMOUNT_TOLERANCE", "FAIL", "REVIEW",
        f"Invoice amount {invoice_amount} exceeds PO '{po.po_number}''s remaining balance of {remaining} "
        f"by {variance_pct:.1f}%, beyond the {allowed:.1f}% tolerance.",
        expected=remaining, actual=invoice_amount, variance_pct=variance_pct, allowed_variance_pct=allowed,
    )


def _best_po_line(description: str, po_lines: list) -> tuple[object | None, float]:
    best_line, best_score = None, 0.0
    for po_line in po_lines:
        score = fuzz.token_sort_ratio(description, po_line.description)
        if score > best_score:
            best_line, best_score = po_line, score
    return best_line, best_score


def check_line_item_reconciliation(invoice: Invoice) -> ValidationResult | None:
    if not invoice.matched_po_id:
        return None

    po_lines = [l for l in invoice.matched_po.line_items if l.description]
    invoice_lines = [l for l in invoice.line_items if l.description]
    if len(po_lines) <= 1 or not invoice_lines:
        return None

    unmatched = [l.description for l in invoice_lines if _best_po_line(l.description, po_lines)[1] < LINE_ITEM_MATCH_THRESHOLD]
    if not unmatched or len(invoice_lines) >= len(po_lines):
        return None

    return _result(
        invoice.id, "LINE_ITEM_RECONCILIATION", "FAIL", "REVIEW",
        f"Invoice has {len(invoice_lines)} line item(s) against PO "
        f"'{invoice.matched_po.po_number}''s {len(po_lines)} line items, and "
        f"{len(unmatched)} of them ({', '.join(unmatched)}) don't map confidently to any single "
        "PO line. This looks like a bundled invoice that cannot be safely reconciled at "
        "line-item level.",
    )


def check_unit_price_tolerance(invoice: Invoice) -> list[ValidationResult]:
    if not invoice.matched_po_id:
        return []

    po_lines = [l for l in invoice.matched_po.line_items if l.description]
    allowed = Decimal(str(UNIT_PRICE_TOLERANCE_PCT))
    results = []

    for line in invoice.line_items:
        if not line.description or line.unit_price is None or not po_lines:
            continue
        best_line, best_score = _best_po_line(line.description, po_lines)
        if not best_line or best_score < LINE_ITEM_MATCH_THRESHOLD or not best_line.unit_price:
            continue

        variance_pct = abs(line.unit_price - best_line.unit_price) / best_line.unit_price * 100
        status = "PASS" if variance_pct <= allowed else "FAIL"
        results.append(_result(
            invoice.id, "UNIT_PRICE_TOLERANCE", status, "BLOCKING" if status == "FAIL" else None,
            f"Line '{line.description}' unit price {line.unit_price} vs PO line "
            f"'{best_line.description}' unit price {best_line.unit_price} "
            f"({variance_pct:.1f}% variance, {allowed:.1f}% allowed).",
            expected=best_line.unit_price, actual=line.unit_price,
            variance_pct=variance_pct, allowed_variance_pct=allowed,
        ))

    return results


def check_quantity(invoice: Invoice) -> list[ValidationResult]:
    if not invoice.matched_po_id:
        return []

    po_lines = [l for l in invoice.matched_po.line_items if l.description]
    results = []

    for line in invoice.line_items:
        if not line.description or line.quantity is None or not po_lines:
            continue
        best_line, best_score = _best_po_line(line.description, po_lines)
        if not best_line or best_score < LINE_ITEM_MATCH_THRESHOLD or best_line.quantity is None:
            continue

        status = "PASS" if line.quantity <= best_line.quantity else "FAIL"
        results.append(_result(
            invoice.id, "QUANTITY_VALIDATION", status, "REVIEW" if status == "FAIL" else None,
            f"Line '{line.description}' quantity {line.quantity} vs PO line "
            f"'{best_line.description}' ordered quantity {best_line.quantity}.",
            expected=best_line.quantity, actual=line.quantity,
        ))

    return results


def run_reconciliation(db: Session, invoice: Invoice) -> list[ValidationResult]:
    results = [check_vendor_match(invoice), check_po_match(invoice)]
    for maybe in (
        check_currency_match(invoice),
        check_po_remaining_balance(invoice),
        check_line_item_reconciliation(invoice),
    ):
        if maybe is not None:
            results.append(maybe)
    results += check_unit_price_tolerance(invoice)
    results += check_quantity(invoice)

    for result in results:
        db.add(result)
    return results
