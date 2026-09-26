import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import NavLinks from "@/components/NavLinks";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ReconFlow",
  description: "AP invoice processing — from PDF to decision",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-gradient-to-b from-slate-50 to-white text-slate-900">
        <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/85 backdrop-blur-sm">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white shadow-sm shadow-indigo-600/30">
                R
              </span>
              <span className="flex flex-col leading-none">
                <span className="text-base font-semibold tracking-tight text-slate-900">ReconFlow</span>
                <span className="text-[11px] text-slate-400">AP Invoice Processing</span>
              </span>
            </Link>
            <NavLinks />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">{children}</main>
        <footer className="border-t border-slate-200 py-6 text-center text-xs text-slate-400">
          ReconFlow — automated invoice reconciliation
        </footer>
      </body>
    </html>
  );
}
