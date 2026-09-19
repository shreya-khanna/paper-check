"use client";

import { useState } from "react";
import { InputPanel } from "@/components/InputPanel";
import { ReportView } from "@/components/ReportView";
import type { Report } from "@/lib/types";

export default function Home() {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function analyze(data: FormData) {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const res = await fetch("/api/analyze", { method: "POST", body: data });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? `Request failed with status ${res.status}.`);
      }
      setReport((await res.json()) as Report);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="site-header">
        <div className="shell">
          <span className="wordmark">Paper Check</span>
        </div>
      </header>

      <main className="shell">
        <section className="intro">
          <h1>Check a paper&apos;s methods before you cite it</h1>
          <p>
            Enter a DOI or arXiv ID, or upload a PDF. You get a checklist of what the paper
            reports, where its methods look inconsistent, and whether its claims match what it
            tested.
          </p>
        </section>

        <InputPanel onSubmit={analyze} loading={loading} />

        {loading && (
          <p className="status-line" role="status">
            Reading the paper and checking its methods. This can take a minute.
          </p>
        )}

        {error && (
          <div className="notice" role="alert">
            <strong>The check did not finish.</strong> {error} Try again, or upload the PDF
            instead.
          </div>
        )}

        {report && <ReportView report={report} />}
      </main>
    </>
  );
}
