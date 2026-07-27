import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Suggested Team"
};

export default function SuggestedTeamLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
