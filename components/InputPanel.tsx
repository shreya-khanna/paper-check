"use client";

import { useState } from "react";

type Mode = "identifier" | "pdf";

export function InputPanel({
  onSubmit,
  loading,
}: {
  onSubmit: (data: FormData) => void;
  loading: boolean;
}) {
  const [mode, setMode] = useState<Mode>("identifier");
  const [identifier, setIdentifier] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const ready = mode === "identifier" ? identifier.trim().length > 0 : file !== null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!ready || loading) return;
    const data = new FormData();
    if (mode === "identifier") data.append("identifier", identifier.trim());
    else if (file) data.append("file", file);
    onSubmit(data);
  }

  return (
    <form className="input-panel" onSubmit={handleSubmit}>
      <div className="segmented" role="group" aria-label="Input type">
        <button
          type="button"
          aria-pressed={mode === "identifier"}
          onClick={() => setMode("identifier")}
        >
          DOI or arXiv ID
        </button>
        <button type="button" aria-pressed={mode === "pdf"} onClick={() => setMode("pdf")}>
          Upload PDF
        </button>
      </div>

      {mode === "identifier" ? (
        <div className="field">
          <label htmlFor="identifier">DOI or arXiv ID</label>
          <input
            id="identifier"
            type="text"
            value={identifier ?? ""}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="10.1000/xyz123 or 2401.01234"
            autoComplete="off"
          />
        </div>
      ) : (
        <div className="field">
          <label htmlFor="pdf">PDF file</label>
          <input
            id="pdf"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
      )}

      <button className="primary" type="submit" disabled={!ready || loading}>
        {loading ? "Checking paper" : "Check paper"}
      </button>
    </form>
  );
}
