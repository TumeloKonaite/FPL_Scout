import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Admin sign in"
};

export default function AdminLoginLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
