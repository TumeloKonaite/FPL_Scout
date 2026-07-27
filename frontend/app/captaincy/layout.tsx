import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Captaincy"
};

export default function CaptaincyLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
