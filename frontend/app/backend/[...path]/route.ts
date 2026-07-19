import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const apiTarget = (process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/$/, "");

  const { path } = await context.params;
  const target = new URL(`/${path.join("/")}`, apiTarget);
  target.search = request.nextUrl.search;
  const headers = new Headers();
  for (const name of ["accept", "content-type"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const isPipelineMutation = request.method === "POST" && path.join("/") === "api/pipeline-runs";
  if (isPipelineMutation && process.env.PIPELINE_API_TOKEN) {
    headers.set("authorization", `Bearer ${process.env.PIPELINE_API_TOKEN}`);
  }

  try {
    const response = await fetch(target, {
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      headers,
      method: request.method
    });
    return new NextResponse(response.body, {
      headers: {
        "content-type": response.headers.get("content-type") ?? "application/json"
      },
      status: response.status,
      statusText: response.statusText
    });
  } catch {
    return NextResponse.json(
      { detail: "The FPL API is unavailable. Check the Modal API deployment and API_PROXY_TARGET." },
      { status: 502 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
