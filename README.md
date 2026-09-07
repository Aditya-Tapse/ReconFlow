# Invoice AI — AP Invoice Processing

Status: Day 1 of the 7-day plan. Backend foundation only — PDF extraction, matching,
validation, and the decision engine come in later days.

## What works right now

- FastAPI backend with a SQLite database (via SQLAlchemy)
- Full data model: Vendor, PurchaseOrder, POLineItem, Invoice, InvoiceLineItem,
  ValidationResult, Decision, AuditEvent
- Seed script loading 6 vendors and 10 purchase orders (with line items) from
  `sample_data/`
- `POST /api/invoices` — upload a PDF, creates an invoice case, stores the file,
  sets status to `PROCESSING`, and logs an `INVOICE_RECEIVED` audit event
- `GET /api/invoices` — list invoice cases
- `GET /api/invoices/{id}` — fetch one invoice case
- `GET /api/invoices/{id}/audit-trail` — view audit events for a case

## Setup

```bash
cd backend
pip install -r requirements.txt
python -m app.seed          # loads vendors + purchase orders
uvicorn app.main:app --reload
```

Server runs at `http://127.0.0.1:8000`. Interactive API docs at `/docs`.

## Try it

```bash
curl -X POST http://127.0.0.1:8000/api/invoices \
  -F "file=@/path/to/invoice.pdf;type=application/pdf"

curl http://127.0.0.1:8000/api/invoices
curl http://127.0.0.1:8000/api/invoices/1/audit-trail
```

## Project layout

```text
invoice-ai/
├── frontend/                 placeholder, built in Day 6
├── backend/
│   ├── app/
│   │   ├── main.py           FastAPI app, router registration
│   │   ├── database.py       SQLAlchemy engine/session
│   │   ├── seed.py           loads sample_data/ into the DB
│   │   ├── api/invoices.py   upload + read endpoints
│   │   ├── models/           ORM models for all entities
│   │   ├── schemas/          Pydantic response models
│   │   ├── services/audit.py audit event logging
│   │   └── utils/            file storage, vendor name normalization
│   ├── uploads/               stored invoice PDFs
│   └── requirements.txt
├── sample_data/
│   ├── vendors.json
│   └── purchase_orders.json
└── README.md
```

## Notes on the seed data

`PO-1001` is pre-loaded with `invoiced_amount = 75000` against a `total_amount`
of `100000`, simulating two prior invoices already consumed against it — this
sets up the cumulative/split-PO overbilling edge case for Day 5.
`PO-1008` has three separate line items (Laptop, Dock, Keyboard) that sum to
its total — this sets up the bundled-invoice-vs-itemized-PO edge case.

## Next: Day 2

PDF text extraction (PyMuPDF), OCR fallback for scanned invoices, and LLM-based
structured extraction into the `ExtractedInvoice` schema.
