from app.services.vendor_matching import match_vendor
from tests.conftest import make_invoice


def test_match_by_tax_id(db, vendor):
    invoice = make_invoice(db, vendor_tax_id=vendor.tax_id, vendor_name="Some Other Spelling Ltd")
    result = match_vendor(db, invoice)
    assert result["vendor"].id == vendor.id
    assert result["method"] == "TAX_ID"
    assert result["confidence"] == 100.0


def test_match_by_normalized_name(db, vendor):
    invoice = make_invoice(db, vendor_tax_id=None, vendor_name="ACME Technologies")
    result = match_vendor(db, invoice)
    assert result["vendor"].id == vendor.id
    assert result["method"] == "NORMALIZED_NAME"


def test_fuzzy_match_above_threshold(db, vendor):
    invoice = make_invoice(db, vendor_tax_id=None, vendor_name="Acme Technologiess")
    result = match_vendor(db, invoice)
    assert result["vendor"].id == vendor.id
    assert result["method"] == "FUZZY_NAME"
    assert result["confidence"] >= 85


def test_no_match_for_unrelated_name(db, vendor):
    invoice = make_invoice(db, vendor_tax_id=None, vendor_name="Totally Unrelated Corporation")
    result = match_vendor(db, invoice)
    assert result["vendor"] is None
    assert result["method"] == "NONE"


def test_no_match_when_vendor_name_and_tax_id_missing(db, vendor):
    invoice = make_invoice(db, vendor_tax_id=None, vendor_name=None)
    result = match_vendor(db, invoice)
    assert result["vendor"] is None
    assert result["confidence"] == 0.0


def test_tax_id_takes_priority_over_worse_name(db, vendor, other_vendor):
    invoice = make_invoice(db, vendor_tax_id=other_vendor.tax_id, vendor_name="Acme Technologies")
    result = match_vendor(db, invoice)
    assert result["vendor"].id == other_vendor.id
    assert result["method"] == "TAX_ID"
