import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: {
    default: "Administration",
    template: "%s · kasifpl"
  }
};

export default function AdminLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
