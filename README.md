# ReconFlow

**AP invoice processing, from PDF to decision.** Upload a vendor invoice, and
ReconFlow extracts its data, matches it to the right purchase order,
reconciles the numbers, and returns a clear APPROVED / MANUAL_REVIEW /
REJECTED decision — with every step of the reasoning visible and auditable.

---

## 1. The problem

A finance team receives vendor invoices as PDFs — some clean and
machine-readable, some scanned images. For each one, someone has to:

- read the invoice and figure out which vendor and purchase order it belongs to
- check the PO reference, or work it out if it's missing
- verify the math, the prices, the quantities
- check it isn't a duplicate of something already paid
- decide whether to pay it, reject it, or escalate it for review

This is repetitive, it's slow, and a lot of the judgment calls involved
("does this invoice bundle several PO line items into one?", "has this PO
already been partially consumed by an earlier invoice?") are exactly the
kind of thing a tired person on a Friday afternoon gets wrong.

## 2. The solution

ReconFlow automates the whole path from PDF to decision, built on one
governing principle:

> **Use AI for ambiguity and unstructured information. Use deterministic
> code for financial rules and the final decision.**

An LLM reads the PDF and turns it into structured data — that's a job
suited to a language model, because invoice layouts vary and the model can
read a scanned image the same way a human would. Everything after that —
matching, arithmetic, tolerances, and the approve/reject decision — is
plain, deterministic Python. The same input always produces the same
decision, and every decision traces back to a rule you can read.

## 3. Architecture

```text
Invoice PDF
    │
    ▼
Document ingestion (upload, stored, case created)
    │
    ▼
PDF text extraction (PyMuPDF) ──low/no text──▶ Vision-based OCR fallback
    │                                                   │
    └───────────────────┬───────────────────────────────┘
                         ▼
        LLM structured extraction (ExtractedInvoice + evidence)
                         │
                         ▼
              Invoice-level validation
        (required fields, arithmetic, duplicate check)
                         │
                         ▼
                  Vendor matching
        (tax ID → normalized name → fuzzy name)
                         │
                         ▼
              Purchase order matching
   (explicit PO reference, or scored candidates if missing)
                         │
                         ▼
                  Reconciliation
 (vendor/currency match, PO remaining balance, unit price
        and quantity tolerance, bundled-invoice check)
                         │
                         ▼
              Deterministic decision engine
                         │
                         ▼
        APPROVED / MANUAL_REVIEW / REJECTED
      + reason, evidence, and full audit trail
```

Two services, talking over HTTP:

- **Backend** (`backend/`) — FastAPI + SQLAlchemy + SQLite. Owns the entire
  pipeline above and exposes it as a REST API.
- **Frontend** (`frontend/`) — Next.js + TypeScript + Tailwind. A dashboard,
  upload flow, and a per-invoice decision screen with the full processing
  timeline and evidence panels. Talks to the backend purely over `fetch`;
  there's no server-side coupling between the two.

## 4. Processing pipeline

Each stage is a small, focused Python module under `backend/app/services/`,
run synchronously in sequence when an invoice is uploaded (`api/invoices.py`
calls each stage in turn):

1. **Ingestion** — the PDF is stored, an `Invoice` case row is created with
   status `PROCESSING`, and an `INVOICE_RECEIVED` audit event is logged.
2. **Extraction** (`pdf_processing.py`, `llm/`, `invoice_extraction.py`) —
   native text is pulled with PyMuPDF; if there's not enough of it
   (< 100 characters), the page is rendered to an image and a vision-capable
   model reads it instead. Either way, a single LLM call returns a
   schema-validated `ExtractedInvoice` (vendor, invoice number, date, PO
   reference, currency, line items, subtotal/tax/total) plus a list of
   evidence entries — the exact source text each field was read from.
   Missing fields come back as `null`, never guessed. Status becomes
   `EXTRACTED`, or `EXTRACTION_FAILED` if the whole step throws.
3. **Validation** (`validation.py`, `duplicate_detection.py`) — required
   fields present, line/subtotal/total arithmetic within a ±1.00 rounding
   tolerance, and a duplicate check against every other invoice in the
   system by business identifiers (vendor + invoice number, or vendor + date
   + total) — never by file hash.
4. **Vendor matching** (`vendor_matching.py`) — tax ID exact match, then
   normalized-name exact match, then RapidFuzz fuzzy match, in that priority
   order. Each match carries a confidence score and a plain-language reason.
5. **PO matching** (`po_matching.py`) — if the invoice states a PO number,
   it's looked up and checked against the matched vendor (a PO belonging to
   someone else is refused, never silently matched). If there's no PO
   number, every open PO for the matched vendor is scored and ranked (see
   §6) and the full candidate list is kept, not just the winner.
6. **Reconciliation** (`reconciliation.py`) — vendor/currency consistency,
   the invoice amount against the PO's *remaining* balance, per-line unit
   price and quantity tolerance, and a check for bundled invoices that can't
   be safely reconciled line-by-line. Status becomes `VALIDATED`.
7. **Decision** (`decision_engine.py`) — a pure function over every
   `ValidationResult` produced above: any `BLOCKING` failure rejects, any
   remaining `REVIEW` failure sends it to manual review, otherwise it's
   approved. The reason is assembled directly from the failing rules'
   messages — nothing here is generated by an LLM. Status becomes the
   decision itself (`APPROVED` / `MANUAL_REVIEW` / `REJECTED`), and every
   step along the way is recorded as an `AuditEvent`.

## 5. Design decisions

**Why the LLM never makes the final decision.** LLMs are good at reading
unstructured documents and resolving ambiguity — what a scanned invoice
says, whether "Employee workstation package" plausibly means "laptop + dock
+ keyboard." They are the wrong tool for "should we pay this" — that needs
to be reproducible, explainable, and unaffected by model updates or
sampling. So extraction is the LLM's job, and matching/reconciliation/decision
is Python's.

**Why the PO's *remaining* balance, not its total.** A PO is often consumed
across several invoices. Comparing a new invoice only to the PO's original
total would let it approve an invoice that, combined with what's already
been paid, blows through the PO — exactly the mistake a rushed manual
reviewer makes. `PO_AMOUNT_TOLERANCE` always compares against
`total_amount − invoiced_amount`.

**Why vendor matching runs before duplicate/PO checks.** Everything
downstream — which PO pool to search, whose invoices count as "the same
vendor" for duplicate detection — depends on knowing the vendor first, and
vendor identity is resolved through three independent signals (tax ID, exact
normalized name, fuzzy name) so a slightly different company-name spelling
doesn't derail the whole pipeline.

**Why a pluggable LLM provider.** Extraction quality and cost are a real
tradeoff, and the right choice differs by context — Ollama is free and
fully local, OpenAI/Anthropic are more reliable but cost money and need a
key. `LLM_PROVIDER` swaps the entire extraction backend with no code
changes (see `backend/app/services/llm/`), and the schema, prompt, and
downstream pipeline are identical regardless of which one is active.

**Why evidence and a full audit trail.** A rejected or flagged invoice is
useless to a reviewer if they can't see *why*. Every extracted field that
matters can be traced back to the exact text it came from
(`GET /api/invoices/{id}/evidence`), every processing step is timestamped
(`GET /api/invoices/{id}/audit-trail`), and every rule that ran is visible
with its pass/fail status and message
(`GET /api/invoices/{id}/validation-results`) — not just the ones that
failed.

## 6. Decision rules

Every rule below produces a `ValidationResult` row (`rule_id`, `status`,
`severity`, `message`, and where relevant `expected`/`actual`/`variance_pct`).
The decision engine is purely mechanical from there:

```text
if any result has severity BLOCKING and status FAIL:  REJECTED
elif any result has severity REVIEW and status FAIL:   MANUAL_REVIEW
else:                                                   APPROVED
```

| Rule | Checks | On failure |
|---|---|---|
| `REQUIRED_FIELD_*` | invoice number, date, vendor, total, currency all present | REVIEW |
| `ARITHMETIC_LINE_TOTAL` | quantity × unit price ≈ line amount (±1.00) | REVIEW |
| `ARITHMETIC_SUBTOTAL` | Σ line amounts ≈ subtotal (±1.00) | REVIEW |
| `ARITHMETIC_TOTAL` | subtotal + tax ≈ total (±1.00) | REVIEW |
| `DUPLICATE_CHECK` | same vendor + invoice number → strong duplicate; same vendor + date + total → possible duplicate | **BLOCKING** (strong) / REVIEW (possible) |
| `VENDOR_MATCH` | a vendor was confidently matched | **BLOCKING** |
| `PO_MATCH` | a purchase order was confidently matched | REVIEW |
| `CURRENCY_MATCH` | invoice currency = matched PO's currency | **BLOCKING** |
| `PO_AMOUNT_TOLERANCE` | invoice amount vs. PO's *remaining* balance, ±2% | REVIEW |
| `UNIT_PRICE_TOLERANCE` | per line, invoice unit price vs. matched PO line, ±2% | **BLOCKING** |
| `QUANTITY_VALIDATION` | invoice quantity ≤ matched PO line's ordered quantity | REVIEW |
| `LINE_ITEM_RECONCILIATION` | invoice line items map confidently to PO line items (bundling check) | REVIEW |

Vendor matching (tax ID → normalized name → fuzzy, threshold 85%) and PO
candidate scoring (40% vendor + 30% amount-vs-remaining-balance + 20%
line-item similarity + 10% date proximity; ≥90% auto-matches, 70–90% needs
review, below that is unmatched) sit upstream of these rules — see §4. All
thresholds are environment-configurable (`backend/app/config.py`).

## 7. Edge cases

Four scenarios where the happy path doesn't apply, each with a working
sample invoice under `sample_data/invoices/`:

**Split PO / cumulative overbilling.** `PO-1001` already has ₹75,000
invoiced against its ₹100,000 total (₹25,000 remaining).
`invoice_acme_po1001_overbilling.pdf` bills ₹30,000 against it — 20% over
the remaining balance, well past the 2% tolerance. Result: `MANUAL_REVIEW`,
with the reason naming the exact remaining balance and the overage.

**Missing PO reference.** `invoice_acme_no_po_reference.pdf` doesn't state
a PO number at all. The system searches every open PO for the matched
vendor, scores each one, and finds `PO-1002` at ~99.6% confidence — high
enough to auto-match. All scored candidates (not just the winner) are kept
and visible via `GET /api/invoices/{id}/po-candidates`.

**Duplicate invoice via a different file.** A vendor might resend the same
invoice as a rescan, a reformatted PDF, or a renamed file.
`invoice_acme_po1002_rescanned_duplicate.pdf` is a completely different PDF
(image-based, so it takes the OCR path) but describes the same invoice
number for the same vendor as `invoice_acme_po1002.pdf`. Because
`DUPLICATE_CHECK` matches on business identifiers, never file hash or
extraction method, it's still caught: `REJECTED`.

**Bundled invoice vs. itemized PO.** `PO-1008` has three separate line items
(Laptop ₹70,000, Docking station ₹8,000, Keyboard ₹2,000).
`invoice_vertex_po1008_bundled.pdf` bills the same ₹80,000 as one line,
"Employee workstation package." The system can match the invoice to the PO
overall, but `LINE_ITEM_RECONCILIATION` recognizes it can't safely map that
one bundled line onto three separate PO lines, and deliberately refuses to
guess: `MANUAL_REVIEW`, not a false `APPROVED`.

## 8. Sample scenarios

| File | Exercises | Expected decision |
|---|---|---|
| `invoice_acme_po1002.pdf` | native-text extraction, explicit PO reference, exact match | `APPROVED` |
| *(the same file, uploaded again)* | duplicate detection | `REJECTED` |
| `invoice_acme_no_po_reference.pdf` | PO candidate scoring, no PO reference stated | `APPROVED` |
| `invoice_acme_po1001_overbilling.pdf` | invoice amount exceeds the PO's remaining balance | `MANUAL_REVIEW` |
| `invoice_acme_po1002_rescanned_duplicate.pdf` | duplicate detection across a different PDF file | `REJECTED` |
| `invoice_vertex_po1008_bundled.pdf` | bundled invoice vs. an itemized PO | `MANUAL_REVIEW` |
| `invoice_globaloffice_scanned.pdf` | image-only PDF, OCR/vision extraction fallback | typically `APPROVED` — see the note on Ollama reliability in §10 |

Regenerate or extend these with `python scripts/generate_sample_invoices.py`
(run from `backend/`).

## 9. Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| Database | SQLite (dev) / Postgres (deployment) via SQLAlchemy, swapped with `DATABASE_URL` |
| Validation / schemas | Pydantic |
| PDF parsing | PyMuPDF |
| Structured extraction + vision OCR | Ollama (local) / OpenAI / Anthropic / Gemini — pluggable |
| Fuzzy matching | RapidFuzz |
| File storage | Local `uploads/` directory |
| Backend testing | Pytest |
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS |

## 10. Setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # then edit .env — see "LLM provider" below
python -m app.seed          # loads vendors + purchase orders
uvicorn app.main:app --reload
```

API runs at `http://127.0.0.1:8000`; interactive docs at `/docs`.

#### LLM provider

Extraction needs one working provider, set in `backend/.env`:

| `LLM_PROVIDER` | Requires |
|---|---|
| `ollama` (default) | A local Ollama server (`ollama serve`) with `OLLAMA_MODEL` (default `llama3.2`) and `OLLAMA_VISION_MODEL` (default `llama3.2-vision`) pulled |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `gemini` | `GEMINI_API_KEY` |

Ollama is free and local, but the default small model is noticeably less
reliable at structured extraction than OpenAI/Anthropic — and the vision
fallback used for scanned PDFs is the least reliable of the three paths; it
can miss a field or an evidence entry on a given run even though the page
renders fine. The pipeline handles that safely (missed fields stay `null`,
nothing crashes), but for consistent results on the OCR path, `openai` or
`anthropic` extract more completely.

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at the backend API, defaults to localhost:8000
npm run dev
```

Runs at `http://localhost:3000`. Requires the backend to be running.

### Try it

```bash
curl -X POST http://127.0.0.1:8000/api/invoices \
  -F "file=@/path/to/invoice.pdf;type=application/pdf"

curl http://127.0.0.1:8000/api/invoices
curl http://127.0.0.1:8000/api/invoices/1/audit-trail
curl http://127.0.0.1:8000/api/invoices/1/evidence
curl http://127.0.0.1:8000/api/invoices/1/validation-results
curl http://127.0.0.1:8000/api/invoices/1/po-candidates
curl http://127.0.0.1:8000/api/invoices/1/decision
```

or just open `http://localhost:3000` and upload a PDF from
`sample_data/invoices/` — the UI shows the same data as the API, rendered.

### Tests

```bash
cd backend
pytest
```

54 tests cover the deterministic rule engine — validation, duplicate
detection, vendor matching, PO matching (explicit and candidate-scored),
PO balance/amount/quantity tolerance, the bundled-invoice check, and the
decision engine itself — using an in-memory SQLite database and
hand-constructed invoices, independent of any LLM provider. Extraction
itself isn't unit-tested (it's inherently non-deterministic across
providers/models); it's covered by the sample invoices in §8 instead.

## 11. API reference

| Endpoint | Description |
|---|---|
| `POST /api/invoices` | Upload a PDF; runs the full pipeline synchronously and returns the case ID + final status |
| `GET /api/invoices` | List all invoice cases |
| `GET /api/invoices/{id}` | Full invoice detail — extracted fields, line items, matched vendor/PO |
| `GET /api/invoices/{id}/file` | The original uploaded PDF |
| `GET /api/invoices/{id}/audit-trail` | Every processing event, in order, with timestamps |
| `GET /api/invoices/{id}/evidence` | Source text for each extracted field |
| `GET /api/invoices/{id}/validation-results` | Every rule that ran, pass or fail, with its reason |
| `GET /api/invoices/{id}/po-candidates` | Scored PO candidates when there was no explicit PO reference |
| `GET /api/invoices/{id}/decision` | The final decision and its reason |

## 12. Project structure

```text
reconflow/
├── backend/
│   ├── app/
│   │   ├── main.py                    FastAPI app, router registration
│   │   ├── config.py                  env-driven settings — LLM provider, models, all rule thresholds
│   │   ├── database.py                SQLAlchemy engine/session
│   │   ├── seed.py                    loads sample_data/ into the DB
│   │   ├── api/invoices.py            every HTTP endpoint
│   │   ├── models/                    Vendor, PurchaseOrder, Invoice, ValidationResult, Decision, AuditEvent, ...
│   │   ├── schemas/                   Pydantic request/response + extraction models
│   │   ├── services/
│   │   │   ├── audit.py                 audit event logging
│   │   │   ├── pdf_processing.py        PyMuPDF text extraction + page rendering
│   │   │   ├── llm/                     pluggable extraction (ollama / openai / anthropic)
│   │   │   ├── invoice_extraction.py    orchestrates extraction + persistence
│   │   │   ├── validation.py            required-field + arithmetic checks
│   │   │   ├── duplicate_detection.py   strong/possible duplicate checks
│   │   │   ├── vendor_matching.py       tax ID / normalized name / fuzzy vendor matching
│   │   │   ├── po_matching.py           explicit-reference + candidate-scoring PO matching
│   │   │   ├── invoice_processing.py    orchestrates validation + matching
│   │   │   ├── reconciliation.py        vendor/currency/amount/price/quantity/bundling rules
│   │   │   └── decision_engine.py       deterministic APPROVED/REVIEW/REJECTED decision
│   │   └── utils/                     file storage, vendor name normalization
│   ├── tests/                         pytest suite for the deterministic rule engine
│   ├── scripts/generate_sample_invoices.py   builds the test PDFs in sample_data/invoices/
│   ├── uploads/                       stored invoice PDFs
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx               dashboard — every invoice, its PO, its status
│       │   ├── upload/page.tsx        drag-and-drop upload
│       │   └── invoices/[id]/page.tsx decision screen — timeline, rules, evidence, candidates, PDF
│       ├── components/                StatusBadge, ProcessingTimeline, ValidationResultsTable, Collapsible
│       └── lib/                       typed API client + formatting helpers
├── sample_data/
│   ├── invoices/                      generated test PDFs, one per scenario (see §8)
│   ├── vendors.json
│   └── purchase_orders.json
└── README.md
```

## 13. Limitations

- **Extraction quality depends on the LLM provider.** The default local
  Ollama models are convenient but noticeably weaker than OpenAI/Anthropic,
  especially on the vision/OCR path — see §10.
- **Synchronous processing.** Upload blocks until the full pipeline
  (extraction → decision) completes — there's no background job queue. Fine
  for a single-user demo; would need async processing (a task queue, status
  polling) under real upload volume.
- **SQLite by default, not built for concurrent writers.** Swap in Postgres
  via `DATABASE_URL` for anything beyond a single-user demo.
- **No authentication or multi-tenancy.** Anyone who can reach the API can
  upload and read every invoice.
- **Line-item matching is fuzzy-text-based.** `UNIT_PRICE_TOLERANCE`,
  `QUANTITY_VALIDATION`, and PO candidate scoring all match invoice lines to
  PO lines by description similarity (RapidFuzz). Very differently-worded
  but equivalent line items can fail to match; the system correctly falls
  back to skipping that check rather than guessing, but that means real
  cases occasionally land in review that a human would approve outright.
- **Quantity tracking is per-invoice, not cumulative.** `PO_AMOUNT_TOLERANCE`
  tracks cumulative dollar consumption across invoices against a PO (via
  `invoiced_amount`), but there's no equivalent cumulative *quantity*
  tracker per PO line — `QUANTITY_VALIDATION` only checks this invoice's
  quantity against the PO line's original ordered quantity.

## 14. Production roadmap

Deliberately out of scope for this build, but the natural next steps for a
real deployment:

- Authentication, roles, and a real approval workflow for `MANUAL_REVIEW`
  cases (who reviews, what they can override, and an audit trail of that
  decision too)
- Postgres + a background job queue (Celery/RQ or similar) so upload
  returns immediately and processing happens asynchronously, with status
  polling or webhooks
- Real procurement/ERP integration (SAP, Oracle, NetSuite, ...) instead of
  a seeded local PO table
- Email inbox ingestion, so invoices don't require manual upload
- Cumulative quantity tracking per PO line, not just cumulative amount
- An evaluation suite for extraction quality across providers/models, so
  provider choice is measured rather than anecdotal
- Rate limiting, request auth, and secrets management for the LLM provider
  keys
- Multi-tenant support, if this serves more than one organization
