import React from "react";

export default function Home() {
  return (
    <main className="relative min-h-screen flex flex-col justify-between overflow-hidden bg-slate-950 text-slate-100">
      {/* Background ambient gradient glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 flex items-center justify-center"
      >
        <div className="h-[480px] w-[720px] rounded-full bg-gradient-to-tr from-indigo-600/20 via-sky-600/15 to-emerald-500/10 blur-[130px]" />
      </div>

      {/* Navigation Header */}
      <header className="w-full border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-sky-600 text-base font-bold text-white shadow-md shadow-indigo-500/20">
              CL
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              Chrono<span className="text-indigo-400">Lex</span>
            </span>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              API: Ready
            </span>
            <span className="hidden sm:inline-flex rounded-full border border-slate-700/60 bg-slate-800/40 px-3 py-1 text-xs text-slate-300">
              Sprint 2 — Step 1
            </span>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-16 text-center">
        <div className="mx-auto max-w-4xl space-y-8">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-300 shadow-sm">
            Regulatory Compliance Intelligence
          </div>

          {/* Main Title & Tagline */}
          <div className="space-y-4">
            <h1
              id="hero-title"
              className="text-5xl font-extrabold tracking-tight sm:text-6xl md:text-7xl bg-gradient-to-b from-white via-slate-100 to-slate-400 bg-clip-text text-transparent"
            >
              ChronoLex
            </h1>
            <p
              id="hero-tagline"
              className="text-xl font-semibold tracking-wide text-indigo-300 sm:text-2xl"
            >
              Find the rule. Know when it applied. See why.
            </p>
          </div>

          {/* Core Description */}
          <p
            id="hero-description"
            className="mx-auto max-w-2xl text-base text-slate-400 sm:text-lg leading-relaxed"
          >
            An AI-powered regulatory compliance assistant that retrieves
            grounded answers from regulatory and compliance documents.
          </p>

          {/* Status Box */}
          <div className="mx-auto max-w-lg rounded-xl border border-slate-800 bg-slate-900/70 p-4 text-left shadow-lg backdrop-blur">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              Current State
            </div>
            <p className="text-sm text-slate-300 font-mono">
              Project initialization complete. RAG functionality is not
              implemented yet.
            </p>
          </div>

          {/* Key Value Cards */}
          <div className="grid grid-cols-1 gap-4 pt-6 sm:grid-cols-3 text-left">
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-5 shadow-sm transition hover:border-slate-700">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-indigo-400">
                01. Time-Aware
              </div>
              <h2 className="text-base font-semibold text-white">
                Historical Versioning
              </h2>
              <p className="mt-1 text-xs text-slate-400 leading-normal">
                Determine the governing rule based on transaction and effective
                dates across amending circulars.
              </p>
            </div>

            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-5 shadow-sm transition hover:border-slate-700">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-sky-400">
                02. Grounded Evidence
              </div>
              <h2 className="text-base font-semibold text-white">
                Zero Hallucinations
              </h2>
              <p className="mt-1 text-xs text-slate-400 leading-normal">
                Rigorous citations with exact circular IDs, paragraphs, and
                explicit refusal when evidence is lacking.
              </p>
            </div>

            <div className="rounded-xl border border-slate-800/80 bg-slate-900/50 p-5 shadow-sm transition hover:border-slate-700">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">
                03. Audit-Ready
              </div>
              <h2 className="text-base font-semibold text-white">
                Compliance Verification
              </h2>
              <p className="mt-1 text-xs text-slate-400 leading-normal">
                Engineered for bank risk officers, legal counsel, and compliance
                auditors requiring complete traceability.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full border-t border-slate-800/80 bg-slate-950/80 py-6 text-center text-xs text-slate-500">
        <div className="mx-auto max-w-6xl px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>ChronoLex &copy; 2026 &mdash; Banking Regulatory RAG Assistant</span>
          <span>Sprint #2 &bull; Foundations &amp; Repository Setup</span>
        </div>
      </footer>
    </main>
  );
}
