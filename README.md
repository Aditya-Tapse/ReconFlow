# ReconFlow — AP Invoice Processing

Status: Day 2 of the 7-day plan. PDF ingestion, extraction, and structured
invoice data are working end-to-end. Matching, validation, and the decision
engine come in later days.

## What works right now

- FastAPI backend with a SQLite database (via SQLAlchemy)
- Full data model: Vendor, PurchaseOrder, POLineItem, Invoice, InvoiceLineItem,
  ValidationResult, Decision, AuditEvent
- Seed script loading 6 vendors and 10 purchase orders (with line items) from
  `sample_data/`
- `POST /api/invoices` — upload a PDF, creates an invoice case, stores the
  file, extracts structured invoice data (see below), and returns the final
  status
- `GET /api/invoices` — list invoice cases
- `GET /api/invoices/{id}` — fetch one invoice case, including extracted
  fields and line items
- `GET /api/invoices/{id}/audit-trail` — view audit events for a case
- `GET /api/invoices/{id}/evidence` — view the source text each extracted
  field was read from
- PDF extraction pipeline: native text via PyMuPDF, with a vision-based OCR
  fallback (page rendered to an image, fed to a vision-capable LLM) when a
  PDF has no usable text layer
- Pluggable LLM provider for structured extraction — `ollama` (default,
  local), `openai`, or `anthropic`, selected via `LLM_PROVIDER` in `.env`
- Missing fields are returned as `null` rather than guessed; extraction
  failures are caught, logged to the audit trail, and leave the invoice in
  `EXTRACTION_FAILED` status instead of crashing the request

## Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # then edit .env — see "LLM provider" below
python -m app.seed          # loads vendors + purchase orders
uvicorn app.main:app --reload
```

Server runs at `http://127.0.0.1:8000`. Interactive API docs at `/docs`.

### LLM provider

Structured extraction needs one working provider, configured in `backend/.env`:

| `LLM_PROVIDER` | Requires |
|---|---|
| `ollama` (default) | A local Ollama server (`ollama serve`) with `OLLAMA_MODEL` (default `llama3.2`) and `OLLAMA_VISION_MODEL` (default `llama3.2-vision`) pulled |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |

Ollama is free and local but a small model (the default `llama3.2`) is
noticeably less reliable at structured extraction than OpenAI/Anthropic, and
the vision fallback (`llama3.2-vision`, used for scanned PDFs) is the least
reliable of the three paths — it can miss individual fields or evidence
entries on a given run even though the same page renders fine visually. The
pipeline handles that safely (missed fields stay `null`, nothing crashes),
but for a live demo of the OCR path, `openai` or `anthropic` will extract
more completely and consistently.

## Try it

```bash
curl -X POST http://127.0.0.1:8000/api/invoices \
  -F "file=@/path/to/invoice.pdf;type=application/pdf"

curl http://127.0.0.1:8000/api/invoices
curl http://127.0.0.1:8000/api/invoices/1/audit-trail
curl http://127.0.0.1:8000/api/invoices/1/evidence
```

Two generated sample invoices are in `sample_data/invoices/` — one
machine-readable (`invoice_acme_po1002.pdf`, exercises the native-text path)
and one image-only to force the OCR/vision fallback
(`invoice_globaloffice_scanned.pdf`). Regenerate or extend them with
`python scripts/generate_sample_invoices.py`.

## Project layout

```text
reconflow/
├── frontend/                        placeholder, built in Day 6
├── backend/
│   ├── app/
│   │   ├── main.py                  FastAPI app, router registration
│   │   ├── config.py                env-driven settings (LLM provider, models, thresholds)
│   │   ├── database.py              SQLAlchemy engine/session
│   │   ├── seed.py                  loads sample_data/ into the DB
│   │   ├── api/invoices.py          upload + read endpoints
│   │   ├── models/                  ORM models for all entities
│   │   ├── schemas/                 Pydantic response + extraction models
│   │   ├── services/
│   │   │   ├── audit.py             audit event logging
│   │   │   ├── pdf_processing.py    PyMuPDF text extraction + page rendering
│   │   │   ├── invoice_extraction.py orchestrates extraction + persistence
│   │   │   └── llm/                 provider-agnostic extraction (ollama/openai/anthropic)
│   │   └── utils/                   file storage, vendor name normalization
│   ├── scripts/generate_sample_invoices.py   builds test PDFs into sample_data/invoices/
│   ├── uploads/                     stored invoice PDFs
│   └── requirements.txt
├── sample_data/
│   ├── invoices/
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

## Next: Day 3

Invoice-level validation (required fields, arithmetic checks), duplicate
detection, vendor matching (tax ID / normalized name / fuzzy), and PO matching
(explicit reference and candidate scoring when the PO reference is missing).
