import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Expert Consensus"
};

export default function ExpertConsensusLayout({ children }: Readonly<{ children: ReactNode }>) {
  return children;
}
