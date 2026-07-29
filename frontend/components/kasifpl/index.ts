// Public API for the KasiFPL component pack.
// Consumers must also import the stylesheet:
//   import "@kasifpl/next-component-pack/styles";
// or copy `styles/kasifpl.css` into the host app.

export * from "./types";

export { KasiFplPageShell, KasiFplFooter } from "./components/KasiFplPageShell";
export type { KasiFplPageShellProps, KasiFplFooterProps } from "./components/KasiFplPageShell";

export { KasiFplHeader } from "./components/KasiFplHeader";
export type { KasiFplHeaderProps } from "./components/KasiFplHeader";

export { KasiFplReportSelector } from "./components/KasiFplReportSelector";
export type { KasiFplReportSelectorProps } from "./components/KasiFplReportSelector";

export { OverviewBriefing, OverviewBriefingFromReport } from "./components/OverviewBriefing";
export type { OverviewBriefingProps } from "./components/OverviewBriefing";

export { DecisionCard } from "./components/DecisionCard";
export type { DecisionCardProps } from "./components/DecisionCard";

export { SuggestedTeamPitch } from "./components/SuggestedTeamPitch";
export type { SuggestedTeamPitchProps } from "./components/SuggestedTeamPitch";

export { SuggestedTeamBench } from "./components/SuggestedTeamBench";
export type { SuggestedTeamBenchProps } from "./components/SuggestedTeamBench";

export { PlayerTile, PlayerDetailsPopover } from "./components/PlayerTile";
export type { PlayerTileProps, PlayerDetailsPopoverProps } from "./components/PlayerTile";

export { TransfersPanel, TransferSwapRow } from "./components/TransfersPanel";
export type { TransfersPanelProps } from "./components/TransfersPanel";

export { CaptaincyPanel } from "./components/CaptaincyPanel";
export type { CaptaincyPanelProps } from "./components/CaptaincyPanel";

export { ExpertConsensusPanel } from "./components/ExpertConsensusPanel";
export type { ExpertConsensusPanelProps } from "./components/ExpertConsensusPanel";

export { ConsensusMatrix } from "./components/ConsensusMatrix";
export type { ConsensusMatrixProps } from "./components/ConsensusMatrix";

export { RecommendationEvidence } from "./components/RecommendationEvidence";
export type { RecommendationEvidenceProps } from "./components/RecommendationEvidence";

export { SourceCard } from "./components/SourceCard";
export type { SourceCardProps } from "./components/SourceCard";

export { ArchiveGrid } from "./components/ArchiveGrid";
export type { ArchiveGridProps } from "./components/ArchiveGrid";

export { ReportLoadingState } from "./components/ReportLoadingState";
export type { ReportLoadingStateProps } from "./components/ReportLoadingState";

export { ReportUnavailableState } from "./components/ReportUnavailableState";
export type { ReportUnavailableStateProps } from "./components/ReportUnavailableState";

export { ApiErrorState } from "./components/ApiErrorState";
export type { ApiErrorStateProps } from "./components/ApiErrorState";

export { SectionUnavailableState } from "./components/SectionUnavailableState";
export type { SectionUnavailableStateProps } from "./components/SectionUnavailableState";

// Utilities intentionally exposed for host apps that need them.
export {
  formatDeadline,
  formatShortDate,
  buildPitchLayout,
  parseFormation,
  consensusLabel,
  SUPPORTED_FORMATIONS,
} from "./components/_shared";
