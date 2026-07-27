import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Transfers"
};

export default function TransfersLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
