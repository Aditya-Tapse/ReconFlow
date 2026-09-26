from decimal import Decimal

from app.services.reconciliation import (
    check_line_item_reconciliation,
    check_quantity,
    check_unit_price_tolerance,
)
from tests.conftest import add_line_item, make_invoice


def test_unit_price_within_tolerance_passes(db, vendor, po):
    invoice = make_invoice(db, matched_po_id=po.id)
    add_line_item(db, invoice, unit_price=Decimal("25100.00"))  # 0.4% over
    results = check_unit_price_tolerance(invoice)
    assert results[0].status == "PASS"


def test_unit_price_exceeds_tolerance_is_blocking(db, vendor, po):
    invoice = make_invoice(db, matched_po_id=po.id)
    add_line_item(db, invoice, unit_price=Decimal("26000.00"))  # 4% over, allowed is 2%
    results = check_unit_price_tolerance(invoice)
    assert results[0].status == "FAIL"
    assert results[0].severity == "BLOCKING"


def test_quantity_within_ordered_passes(db, vendor, po):
    invoice = make_invoice(db, matched_po_id=po.id)
    add_line_item(db, invoice, quantity=Decimal("2"))
    results = check_quantity(invoice)
    assert results[0].status == "PASS"


def test_quantity_exceeding_ordered_is_review(db, vendor, po):
    invoice = make_invoice(db, matched_po_id=po.id)
    add_line_item(db, invoice, quantity=Decimal("5"))
    results = check_quantity(invoice)
    assert results[0].status == "FAIL"
    assert results[0].severity == "REVIEW"


def test_line_with_no_confident_po_match_is_skipped(db, vendor, po):
    invoice = make_invoice(db, matched_po_id=po.id)
    add_line_item(db, invoice, description="Completely unrelated line item")
    assert check_unit_price_tolerance(invoice) == []
    assert check_quantity(invoice) == []


def test_bundled_invoice_against_itemized_po_flags_for_review(db, vendor):
    from app.models import POLineItem, PurchaseOrder

    itemized_po = PurchaseOrder(
        po_number="PO-1008", vendor_id=vendor.id, currency="INR",
        total_amount=Decimal("80000.00"), invoiced_amount=Decimal("0.00"), status="OPEN",
    )
    db.add(itemized_po)
    db.commit()
    db.refresh(itemized_po)
    for description, qty, price in [
        ("Laptop", Decimal("1"), Decimal("70000.00")),
        ("Docking station", Decimal("1"), Decimal("8000.00")),
        ("Keyboard", Decimal("1"), Decimal("2000.00")),
    ]:
        db.add(POLineItem(po_id=itemized_po.id, description=description, quantity=qty, unit_price=price, amount=qty * price))
    db.commit()
    db.refresh(itemized_po)

    invoice = make_invoice(db, matched_po_id=itemized_po.id, subtotal=Decimal("80000.00"))
    add_line_item(
        db, invoice, description="Employee workstation package",
        quantity=Decimal("1"), unit_price=Decimal("80000.00"), amount=Decimal("80000.00"),
    )

    result = check_line_item_reconciliation(invoice)
    assert result is not None
    assert result.status == "FAIL"
    assert result.severity == "REVIEW"
    assert "bundled" in result.message.lower()


def test_itemized_invoice_against_itemized_po_does_not_flag_bundling(db, vendor):
    from app.models import POLineItem, PurchaseOrder

    itemized_po = PurchaseOrder(
        po_number="PO-1008", vendor_id=vendor.id, currency="INR",
        total_amount=Decimal("80000.00"), invoiced_amount=Decimal("0.00"), status="OPEN",
    )
    db.add(itemized_po)
    db.commit()
    db.refresh(itemized_po)
    for description, qty, price in [
        ("Laptop", Decimal("1"), Decimal("70000.00")),
        ("Docking station", Decimal("1"), Decimal("8000.00")),
        ("Keyboard", Decimal("1"), Decimal("2000.00")),
    ]:
        db.add(POLineItem(po_id=itemized_po.id, description=description, quantity=qty, unit_price=price, amount=qty * price))
    db.commit()
    db.refresh(itemized_po)

    invoice = make_invoice(db, matched_po_id=itemized_po.id, subtotal=Decimal("80000.00"))
    for description, qty, price in [
        ("Laptop", Decimal("1"), Decimal("70000.00")),
        ("Docking station", Decimal("1"), Decimal("8000.00")),
        ("Keyboard", Decimal("1"), Decimal("2000.00")),
    ]:
        add_line_item(db, invoice, description=description, quantity=qty, unit_price=price, amount=qty * price)

    assert check_line_item_reconciliation(invoice) is None
