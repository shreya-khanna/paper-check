"use client";

import { useState, useRef } from "react";

export function InputPanel({
  onSubmit,
  loading,
}: {
  onSubmit: (data: FormData) => void;
  loading: boolean;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || loading) return;
    const data = new FormData();
    data.append("file", file);
    onSubmit(data);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf" || droppedFile.name.endsWith(".pdf")) {
        setFile(droppedFile);
      }
    }
  }

  return (
    <form className="input-panel" onSubmit={handleSubmit}>
      <div
        className={`file-dropzone ${dragActive ? "drag-active" : ""} ${file ? "has-file" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            inputRef.current?.click();
          }
        }}
      >
        <input
          ref={inputRef}
          id="pdf-upload"
          type="file"
          accept="application/pdf,.pdf"
          style={{ display: "none" }}
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <div className="dropzone-content">
          <svg
            className="dropzone-icon"
            width="36"
            height="36"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="12" y1="18" x2="12" y2="12" />
            <polyline points="9 15 12 12 15 15" />
          </svg>
          <div className="dropzone-text">
            {file ? (
              <>
                <strong className="file-name">{file.name}</strong>
                <span className="file-size muted">
                  ({(file.size / (1024 * 1024)).toFixed(2)} MB) — Click to change file
                </span>
              </>
            ) : (
              <>
                <strong className="dropzone-prompt">Choose a research paper PDF or drag and drop</strong>
                <span className="muted">Supports academic PDF papers (e.g. AAAI, CVPR, NeurIPS)</span>
              </>
            )}
          </div>
        </div>
      </div>

      <button className="primary" type="submit" disabled={!file || loading}>
        {loading ? "Checking paper methods..." : "Check paper"}
      </button>
    </form>
  );
}

