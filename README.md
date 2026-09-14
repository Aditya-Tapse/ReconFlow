# ReconFlow — AP Invoice Processing

Status: Day 3 of the 7-day plan. PDF ingestion, extraction, validation,
duplicate detection, and vendor/PO matching are working end-to-end. The
reconciliation and decision engine come in Day 4.

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
- `GET /api/invoices/{id}/validation-results` — required-field checks,
  arithmetic checks (line total, subtotal, subtotal+tax=total, ±1.00
  tolerance), and duplicate detection, each as a pass/fail rule with a reason
- `GET /api/invoices/{id}/po-candidates` — ranked PO candidates and their
  score breakdown when the invoice had no explicit PO reference
- Duplicate detection: same vendor + same invoice number is a blocking
  duplicate; same vendor + same date + same total is a possible duplicate
  flagged for review. Both reference the specific prior invoice they matched
- Vendor matching: tax ID exact match → normalized-name exact match →
  RapidFuzz fuzzy match, in that priority order, each with a confidence score
  and reason
- PO matching: an explicit PO reference is looked up and vendor-checked (a
  PO belonging to a different vendor is refused, never auto-matched); with no
  PO reference, open POs for the matched vendor are scored (40% vendor, 30%
  amount against the PO's *remaining* balance, 20% line-item similarity, 10%
  date proximity) and ranked — ≥90% auto-matches, 70–90% is left for manual
  review, below that is unmatched. All candidates and their score breakdown
  are kept, not just the winner
- Invoice reaches `VALIDATED` status once processing completes; processing
  failures are caught and logged the same way extraction failures are

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
curl http://127.0.0.1:8000/api/invoices/1/validation-results
curl http://127.0.0.1:8000/api/invoices/1/po-candidates
```

Generated sample invoices are in `sample_data/invoices/`:
`invoice_acme_po1002.pdf` (native-text, explicit PO reference — matches
PO-1002 exactly), `invoice_acme_no_po_reference.pdf` (same invoice with no PO
reference stated, to exercise candidate scoring), and
`invoice_globaloffice_scanned.pdf` (image-only, to force the OCR/vision
fallback). Regenerate or extend them with
`python scripts/generate_sample_invoices.py`. Uploading
`invoice_acme_po1002.pdf` twice is the easiest way to see duplicate detection
fire.

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
│   │   │   ├── audit.py               audit event logging
│   │   │   ├── pdf_processing.py      PyMuPDF text extraction + page rendering
│   │   │   ├── invoice_extraction.py  orchestrates extraction + persistence
│   │   │   ├── llm/                   provider-agnostic extraction (ollama/openai/anthropic)
│   │   │   ├── validation.py          required-field + arithmetic checks
│   │   │   ├── duplicate_detection.py strong/possible duplicate checks
│   │   │   ├── vendor_matching.py     tax ID / normalized name / fuzzy vendor matching
│   │   │   ├── po_matching.py         explicit-reference + candidate-scoring PO matching
│   │   │   └── invoice_processing.py  orchestrates validation + matching after extraction
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

## Next: Day 4

Reconciliation and the decision engine: vendor/currency match rules,
duplicate → reject, invoice amount vs. the PO's *remaining* balance, unit
price and quantity tolerances, and a deterministic
APPROVED / MANUAL_REVIEW / REJECTED decision built from the validation and
matching results Day 3 already produces.
