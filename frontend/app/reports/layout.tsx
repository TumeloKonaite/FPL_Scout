import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Reports"
};

export default function ReportsLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
