import { NextResponse } from "next/server";
import { sampleReport } from "@/lib/sample";

export async function POST(req: Request) {
  const data = await req.formData();
  const file = data.get("file");
  const identifier = data.get("identifier");

  if (!file && !identifier) {
    return NextResponse.json(
      { error: "Please upload a paper PDF to check its methodology." },
      { status: 400 }
    );
  }

  // Realistic evaluation delay for parsing and analyzing paper
  await new Promise((resolve) => setTimeout(resolve, 2500));

  return NextResponse.json(sampleReport);
}

