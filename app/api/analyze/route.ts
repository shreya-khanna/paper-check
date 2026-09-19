import { NextResponse } from "next/server";
import { sampleReport } from "@/lib/sample";

export async function POST(req: Request) {
  const data = await req.formData();
  const identifier = data.get("identifier");
  const file = data.get("file");

  if (!identifier && !file) {
    return NextResponse.json(
      { error: "Provide a DOI, an arXiv ID, or a PDF." },
      { status: 400 }
    );
  }

  // Set BACKEND_URL in .env.local to forward requests to your Python service.
  // The service should accept the same form fields and return a `Report` (see lib/types.ts).
  const backend = process.env.BACKEND_URL;
  if (backend) {
    try {
      const upstream = await fetch(`${backend}/analyze`, { method: "POST", body: data });
      if (!upstream.ok) {
        return NextResponse.json(
          { error: `The analysis service returned status ${upstream.status}.` },
          { status: 502 }
        );
      }
      return NextResponse.json(await upstream.json());
    } catch {
      return NextResponse.json(
        { error: "Could not reach the analysis service. Check that it is running." },
        { status: 502 }
      );
    }
  }

  // No backend configured: return demo data so the UI can be built and tested.
  await new Promise((resolve) => setTimeout(resolve, 1200));
  return NextResponse.json(sampleReport);
}
