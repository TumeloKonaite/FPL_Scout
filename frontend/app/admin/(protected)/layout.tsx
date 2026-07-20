import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

export const dynamic = "force-dynamic";

export default async function ProtectedAdminLayout({ children }: { children: ReactNode }) {
  const token = (await cookies()).get("fpl_admin_session")?.value;
  if (!token) redirect("/admin/login");

  const apiTarget = (process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000").replace(/\/$/, "");
  let authorized = false;
  try {
    const response = await fetch(`${apiTarget}/api/admin/pipeline/status`, {
      cache: "no-store",
      headers: { authorization: `Bearer ${token}` }
    });
    authorized = response.ok;
  } catch {
    authorized = false;
  }
  if (!authorized) redirect("/admin/login?error=invalid");
  return children;
}
