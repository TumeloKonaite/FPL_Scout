import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "fpl_admin_session";

export async function POST(request: NextRequest) {
  const form = await request.formData();
  const token = String(form.get("token") ?? "").trim();
  if (!token) {
    return NextResponse.redirect(new URL("/admin/login?error=required", request.url), 303);
  }

  const apiTarget = (process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  let authenticated = false;
  try {
    const response = await fetch(`${apiTarget}/api/admin/pipeline/status`, {
      cache: "no-store",
      headers: { authorization: `Bearer ${token}` }
    });
    authenticated = response.ok;
  } catch {
    return NextResponse.redirect(new URL("/admin/login?error=unavailable", request.url), 303);
  }

  if (!authenticated) {
    return NextResponse.redirect(new URL("/admin/login?error=invalid", request.url), 303);
  }

  const response = NextResponse.redirect(new URL("/admin", request.url), 303);
  response.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    maxAge: 60 * 60 * 8,
    path: "/",
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production"
  });
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(COOKIE_NAME, "", { httpOnly: true, maxAge: 0, path: "/" });
  return response;
}
