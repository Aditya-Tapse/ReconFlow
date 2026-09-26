"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { uploadInvoice } from "@/lib/api";

export default function UploadPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<"idle" | "uploading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  function pickFile(f: File | undefined | null) {
    if (!f) return;
    if (f.type !== "application/pdf") {
      setError("Only PDF files are accepted.");
      return;
    }
    setError(null);
    setFile(f);
  }

  async function handleUpload() {
    if (!file) return;
    setStatus("uploading");
    setError(null);
    try {
      const result = await uploadInvoice(file);
      const invoiceId = result.invoice_id.replace("INV_CASE_", "");
      router.push(`/invoices/${invoiceId}`);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Upload Invoice</h1>
      <p className="mt-1 text-sm text-slate-500">
        Upload a PDF invoice. It will be extracted, validated, matched against open purchase
        orders, and reconciled automatically — you&apos;ll land on the decision as soon as it&apos;s ready.
      </p>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pickFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        className={`mt-6 flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-16 text-center shadow-sm transition-colors ${
          dragging
            ? "border-indigo-400 bg-indigo-50/60"
            : "border-slate-300 bg-white hover:border-indigo-300 hover:bg-indigo-50/30"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => pickFile(e.target.files?.[0])}
        />
        <span
          className={`flex h-12 w-12 items-center justify-center rounded-full transition-colors ${
            dragging ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-400"
          }`}
        >
          <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6">
            <path
              d="M7 16a4 4 0 0 1-.5-7.97A5.5 5.5 0 0 1 17 7.5a4 4 0 0 1-.5 8.5M12 11v7m0-7 3 3m-3-3-3 3"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        {file ? (
          <>
            <p className="mt-3 text-sm font-medium text-slate-900">{file.name}</p>
            <p className="mt-1 text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB — click to change</p>
          </>
        ) : (
          <>
            <p className="mt-3 text-sm font-medium text-slate-700">Drag an invoice PDF here</p>
            <p className="mt-1 text-xs text-slate-400">or click to browse</p>
          </>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

      <button
        onClick={handleUpload}
        disabled={!file || status === "uploading"}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm shadow-indigo-600/25 transition-colors hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-300 disabled:shadow-none"
      >
        {status === "uploading" && (
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 animate-spin">
            <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
            <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
        )}
        {status === "uploading" ? "Processing invoice…" : "Upload Invoice"}
      </button>

      {status === "uploading" && (
        <p className="mt-3 text-center text-xs text-slate-500">
          Extracting fields, matching vendor and PO, and reconciling — this runs synchronously and
          can take a few seconds.
        </p>
      )}
    </div>
  );
}
