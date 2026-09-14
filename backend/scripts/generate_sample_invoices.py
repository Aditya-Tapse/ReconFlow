import os

import fitz

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "invoices")

CLEAN_INVOICE = [
    "ACME TECHNOLOGIES PVT LTD",
    "Tax ID: 27AACCA1234F1Z5",
    "",
    "INVOICE",
    "Invoice Number: INV-2026-1045",
    "Invoice Date: 2026-09-05",
    "PO Reference: PO-1002",
    "Currency: INR",
    "",
    "Description                Qty   Unit Price   Amount",
    "Network switch - 24 port    2    25000.00     50000.00",
    "",
    "Subtotal: 50000.00",
    "Tax (18% GST): 9000.00",
    "Total: 59000.00",
]

NO_PO_REFERENCE_INVOICE = [
    "ACME TECHNOLOGIES PVT LTD",
    "Tax ID: 27AACCA1234F1Z5",
    "",
    "INVOICE",
    "Invoice Number: INV-2026-1099",
    "Invoice Date: 2026-09-10",
    "Currency: INR",
    "",
    "Description                Qty   Unit Price   Amount",
    "Network switch - 24 port    2    25000.00     50000.00",
    "",
    "Subtotal: 50000.00",
    "Tax (18% GST): 9000.00",
    "Total: 59000.00",
]

SCANNED_INVOICE = [
    "GLOBAL OFFICE SUPPLIES",
    "Tax ID: 07AABCG4321H1Z9",
    "",
    "INVOICE",
    "Invoice Number: INV-3390",
    "Invoice Date: 2026-09-06",
    "PO Reference: PO-1005",
    "Currency: INR",
    "",
    "Description             Qty   Unit Price   Amount",
    "A4 paper - 50 reams     50    220.00       11000.00",
    "Toner cartridges         4    1000.00       4000.00",
    "",
    "Subtotal: 15000.00",
    "Tax (18% GST): 2700.00",
    "Total: 17700.00",
]


def make_text_pdf(path: str, lines: list[str]) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 60
    for line in lines:
        page.insert_text((50, y), line, fontsize=11)
        y += 20
    doc.save(path)
    doc.close()


def make_scanned_pdf(path: str, lines: list[str]) -> None:
    tmp = fitz.open()
    tmp_page = tmp.new_page(width=595, height=842)
    y = 60
    for line in lines:
        tmp_page.insert_text((50, y), line, fontsize=11)
        y += 20
    image_bytes = tmp_page.get_pixmap(dpi=150).tobytes("png")
    tmp.close()

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=image_bytes)
    doc.save(path)
    doc.close()


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    make_text_pdf(os.path.join(OUT_DIR, "invoice_acme_po1002.pdf"), CLEAN_INVOICE)
    make_text_pdf(os.path.join(OUT_DIR, "invoice_acme_no_po_reference.pdf"), NO_PO_REFERENCE_INVOICE)
    make_scanned_pdf(os.path.join(OUT_DIR, "invoice_globaloffice_scanned.pdf"), SCANNED_INVOICE)
    print(f"Generated sample invoices in {OUT_DIR}")
