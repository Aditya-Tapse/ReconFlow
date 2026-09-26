# ReconFlow Frontend

Next.js (App Router) + TypeScript + Tailwind CSS dashboard for ReconFlow.
See the [project README](../README.md) for the full system overview,
architecture, and setup instructions — this file only covers frontend-specific
commands.

## Development

```bash
npm install
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
npm run dev
```

Runs at `http://localhost:3000`. Requires the backend (`../backend`) to be
running — see the root README for how to start it.

## Structure

- `src/app/page.tsx` — dashboard listing every invoice case
- `src/app/upload/page.tsx` — PDF upload
- `src/app/invoices/[id]/page.tsx` — decision screen: processing timeline,
  validation/reconciliation results, extracted fields, source evidence,
  candidate PO matches, and the original PDF
- `src/lib/api.ts` — typed client for the backend API
- `src/components/` — StatusBadge, ProcessingTimeline, ValidationResultsTable,
  Collapsible

## Other commands

```bash
npm run build   # production build
npm run lint    # eslint
```
