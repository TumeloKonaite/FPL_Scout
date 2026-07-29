# @kasifpl/next-component-pack

Framework-neutral, presentation-only React 19 component pack for the KasiFPL UI.
Drop into a Next.js 15 App Router application (or any React 19 app).

- Pure props-in components — no routing, no data fetching, no mock data
- No TanStack, Supabase, or backend imports
- Single stylesheet (`styles/kasifpl.css`) with `kasifpl-` scoped classes and CSS custom properties
- Every optional/nullable field on the `Report` contract renders safely
- Server-safe by default; only interactive components declare `"use client"`

---

## 1. Install

Copy the whole `kasifpl-next-component-pack/` folder into your host app, for example:

```
frontend/components/kasifpl/
├── components/
├── styles/
├── examples/
├── index.ts
├── types.ts
├── package.json
├── tsconfig.json
└── README.md
```

Peer dependencies (already required by any Next.js 15 app): `react@^19`, `react-dom@^19`.
No other runtime dependencies.

Import the stylesheet **once** in your app (e.g. `app/layout.tsx`):

```tsx
import "@/components/kasifpl/styles/kasifpl.css";
```

Then import components from the pack's public entry:

```tsx
import { KasiFplPageShell, KasiFplHeader, /* … */ } from "@/components/kasifpl";
import type { Report, ReportSelection } from "@/components/kasifpl/types";
```

The pack does **not** apply a global reset. It sets a page background only via `KasiFplPageShell` (opt-in) — leaf components stay safe to embed.

---

## 2. Component inventory

| Component | File | `"use client"` | Purpose |
|---|---|---|---|
| `KasiFplPageShell` | `components/KasiFplPageShell.tsx` | no | Full-height page shell with brand background |
| `KasiFplFooter` | `components/KasiFplPageShell.tsx` | no | Footer strip |
| `KasiFplHeader` | `components/KasiFplHeader.tsx` | **yes** | Sticky header + responsive nav (mobile toggle) |
| `KasiFplReportSelector` | `components/KasiFplReportSelector.tsx` | **yes** | Season / gameweek selects + deadline |
| `OverviewBriefing` / `OverviewBriefingFromReport` | `components/OverviewBriefing.tsx` | no | Weekly briefing card (overview, key risk, notes, conclusion) |
| `DecisionCard` | `components/DecisionCard.tsx` | no | Generic recommendation card |
| `SuggestedTeamPitch` | `components/SuggestedTeamPitch.tsx` | **yes** | Dynamic-formation football pitch |
| `SuggestedTeamBench` | `components/SuggestedTeamBench.tsx` | **yes** | Bench strip |
| `PlayerTile` | `components/PlayerTile.tsx` | **yes** | Interactive player shirt tile |
| `PlayerDetailsPopover` | `components/PlayerTile.tsx` | **yes** | Modal popover with player stats (Esc closes, backdrop click closes) |
| `TransfersPanel` / `TransferSwapRow` | `components/TransfersPanel.tsx` | no | Transfer recommendations, cards or compact swaps |
| `CaptaincyPanel` | `components/CaptaincyPanel.tsx` | no | Ranked captaincy picks |
| `ExpertConsensusPanel` | `components/ExpertConsensusPanel.tsx` | no | Expert reveal cards |
| `ConsensusMatrix` | `components/ConsensusMatrix.tsx` | no | Expert × decisions matrix table |
| `RecommendationEvidence` | `components/RecommendationEvidence.tsx` | no | Support/opposition/alternatives/freshness/sources for one recommendation |
| `SourceCard` | `components/SourceCard.tsx` | no | Renders a `RecommendationSource` (link only when URL is valid) |
| `ArchiveGrid` | `components/ArchiveGrid.tsx` | no | Grid of previous gameweek report cards |
| `ReportLoadingState` | `components/ReportLoadingState.tsx` | no | Skeleton state |
| `ReportUnavailableState` | `components/ReportUnavailableState.tsx` | no | No-report-published state |
| `ApiErrorState` | `components/ApiErrorState.tsx` | **yes** (retry button) | Error state with optional retry |
| `SectionUnavailableState` | `components/SectionUnavailableState.tsx` | no | Small "unavailable" tile used inside sections |

Utilities exported from `index.ts`:
`formatDeadline`, `formatShortDate`, `buildPitchLayout`, `parseFormation`, `consensusLabel`, `SUPPORTED_FORMATIONS`.

Supported formations (dynamically laid out on the pitch): `3-4-3`, `3-5-2`, `4-3-3`, `4-4-2`, `4-5-1`, `5-2-3`, `5-3-2`, `5-4-1`. Unrecognized or missing `formation` falls back to actual bucket counts derived from the supplied starters — never fabricated.

---

## 3. Props (essentials)

Full types live in `types.ts` and per-component `*Props` exports. High-level shape:

- `KasiFplHeader({ navItems, activePage?, brand?, brandHref?, rightSlot?, renderLink? })` — supply `renderLink={({href, children, ...rest}) => <Link href={href} {...rest}>{children}</Link>}` to integrate with Next.js.
- `KasiFplReportSelector({ selection, availableSeasons, availableGameweeks, onSeasonChange?, onGameweekChange?, deadline?, isCurrentReport?, disabled? })`
- `OverviewBriefing({ overview, conclusion?, keyRisk?, fixtureNotes?, waitForNews?, conditionalAdvice? })` or `OverviewBriefingFromReport({ report })`
- `DecisionCard({ recommendation, eyebrow?, showEvidence?, rightSlot? })`
- `SuggestedTeamPitch({ team, interactive?, selectedPlayer?, onSelectPlayer? })`
- `SuggestedTeamBench({ team, interactive? })`
- `PlayerTile({ player, isCaptain?, isViceCaptain?, onSelect? })`
- `PlayerDetailsPopover({ player, onClose })`
- `TransfersPanel({ transfers?, title?, subtitle?, compact? })`
- `CaptaincyPanel({ captaincy?, title?, subtitle?, limit? })`
- `ExpertConsensusPanel({ reveals?, title?, subtitle? })`
- `ConsensusMatrix({ reveals?, title? })`
- `RecommendationEvidence({ recommendation, showSources? })`
- `SourceCard({ source })` — renders a plain card (no link) unless `source.url` is a valid `http(s)://` URL.
- `ArchiveGrid({ entries?, title?, subtitle?, renderLink? })`
- `ReportLoadingState({ label? })`
- `ReportUnavailableState({ title?, message?, action? })`
- `ApiErrorState({ title?, message?, detail?, onRetry?, retryLabel? })`
- `SectionUnavailableState({ title?, message })`

Navigation and selection never call a router — pass `hrefForPage`-style strings via `navItems[].href` and `ArchiveEntry.href`, and use `renderLink` to wire `<Link>`.

---

## 4. Required CSS

Exactly one stylesheet:

```
styles/kasifpl.css
```

All rules are prefixed with `kasifpl-`. There is no Tailwind config requirement and no global reset. CSS custom properties (all `--kasifpl-*`) can be overridden at any ancestor for theming.

Responsive behaviour is baked into `kasifpl.css` at `1440`, `1024`, `768`, and `390` px breakpoints.

---

## 5. External dependencies

None at runtime beyond `react` / `react-dom` (peer). Dev-only types: `@types/react`, `@types/react-dom`, `typescript`.

---

## 6. Lovable-screen → exported component mapping

| Existing Lovable route | Exported components |
|---|---|
| `/` (Briefing / Overview) | `OverviewBriefingFromReport`, `SuggestedTeamPitch`, `CaptaincyPanel` (limit 2), `TransfersPanel` (compact) |
| `/suggested-team` | `SuggestedTeamPitch`, `SuggestedTeamBench`, `PlayerDetailsPopover` |
| `/transfers` | `TransfersPanel` (full cards via `DecisionCard`) |
| `/captaincy` | `CaptaincyPanel` |
| `/expert-analysis` | `ExpertConsensusPanel`, `ConsensusMatrix` |
| `/historical-reports` | `ArchiveGrid` |
| App shell / header (`app-shell.tsx`, `global-header.tsx`) | `KasiFplPageShell`, `KasiFplHeader`, `KasiFplFooter`, `KasiFplReportSelector` |
| Loading / empty / error surfaces (`states.tsx`) | `ReportLoadingState`, `ReportUnavailableState`, `ApiErrorState`, `SectionUnavailableState` |
| Recommendation evidence & sources (`expert-support.tsx`, `source-card.tsx`) | `RecommendationEvidence`, `SourceCard` |

---

## 7. Visual field → backend contract mapping

| Visible element | Contract field |
|---|---|
| Header brand / nav labels | Host-supplied via `KasiFplHeader.navItems` |
| Season / gameweek selects | `ReportSelection.season`, `ReportSelection.gameweek`, `availableSeasons`, `availableGameweeks` |
| Deadline strap | `Report.deadline` → `KasiFplReportSelector.deadline` |
| "Current" chip | `KasiFplReportSelector.isCurrentReport` (host-computed) |
| Briefing paragraph | `Report.overview` |
| Key risk block | `Report.key_risk.{subject, riskType, explanation, recommendedAction}` |
| Wait for news / conditional advice / fixture notes | `Report.wait_for_news[]`, `Report.conditional_advice[]`, `Report.fixture_notes[]` |
| Conclusion paragraph | `Report.conclusion` |
| Decision card title / body | `FinalRecommendation.title`, `.rationale` |
| Player identity line on decision card | `.playerName`, `.club`, `.opponent`, `.venue`, `.price`, `.position` |
| Captaincy vice-captain hint | `FinalRecommendation.viceCaptain` |
| Transfer swap row | `.playerOut` → `.playerIn` |
| Consensus chip | Prefers `consensus.supportCount` / `consensus.relevantExpertCount` / `consensus.label`; falls back to legacy `consensusCount` / `expertCount` only when `consensus` is absent |
| Support bar | `consensus.supportRatio` (fallback: `supportCount / relevantExpertCount`) |
| Opposition chip | `consensus.oppositionCount` (hidden when 0) |
| Mentions chip | `consensus.mentionCount` (hidden when 0; **never counted as support**) |
| Model confidence chip | `FinalRecommendation.confidence` (labelled as model confidence, not consensus) |
| Freshness chips | `freshness.generatedAt`, `.newestSourceAt`, `.sourceWindowHours` |
| Alternatives list | `FinalRecommendation.alternatives[]` |
| Source card body | `RecommendationSource.{name,title,publishedAt,position}` |
| Source card link | `RecommendationSource.url` — only when it's a valid `http(s)://` URL |
| Pitch formation | `SuggestedTeam.formation`; if invalid/missing the actual starter buckets are used |
| Starters / bench | `SuggestedTeam.startingXi` (or `.starters` or `.players` filtered by `isStarter`), `.bench` (or `.players` where `isStarter===false`), ordered by `.benchOrder` |
| Captain / vice badge | `SuggestedTeam.captainPlayerId` / `.viceCaptainPlayerId` matched to `SuggestedPlayer.playerId`, or per-player `captain` / `viceCaptain` |
| Player tile shirt number | `SuggestedPlayer.shirtNumber ?? .number` (falls back to position label) |
| Player popover stats | `SuggestedPlayer.{price, predictedPoints, ownership, expectedMinutes, fixtureDifficulty}` + `support.*` counts |
| Expert reveal card | `ExpertTeamReveal.{expert_name, captain, vice_captain, transfers_in, transfers_out, summary}` |
| Consensus matrix rows | `Report.expert_team_reveals[]` |
| Archive card | `ArchiveEntry.{season, gameweek, deadline, title, summary, href, isCurrent}` (host-composed) |

---

## 8. Mockup fields removed because the contract does not supply them

The current Lovable mockup includes visuals that were removed from the pack because the `Report` contract does not carry the data to render them honestly:

- **YouTube thumbnails, video durations, transcript-availability badges, and expert channel avatars.** `RecommendationSource` has no thumbnail, duration, transcript, or avatar field, so `SourceCard` uses text-only presentation and never fabricates an image.
- **Static hero copy, static "seasoned by X experts" strapline, and illustrative gameweek countdown.** `Report` has no marketing copy; the header/footer accept host-provided children.
- **Faked "Fantasy Manager Score" and confidence-as-consensus badges.** Recommendation confidence is presented only as *model confidence*, clearly distinct from expert consensus. The semantically ambiguous expert-reveal confidence field is not displayed.
- **Fabricated XI when consensus is insufficient.** When `SuggestedTeam.constructionStatus === "insufficient_evidence"` (or when there is no `startingXi`/`starters`/`players`), `SuggestedTeamPitch` renders `SectionUnavailableState` with `failureReason` if supplied — it does **not** synthesize players.
- **Hardcoded "next deadline in Xh Ym" ticker.** Deadline is displayed only when `Report.deadline` is supplied and is formatted with the browser locale.
- **Fabricated support counts.** Opposition/mentions/alternatives chips render only when the backend supplies non-zero values; missing fields hide the chip rather than showing "0 experts oppose" as if verified.

---

## 9. Copy into an existing Next.js `frontend/components/kasifpl/` directory

```bash
# from the root of the export archive
cp -R kasifpl-next-component-pack/. path/to/frontend/components/kasifpl/
```

Then in `frontend/app/layout.tsx` (or a route-group layout):

```tsx
import "@/components/kasifpl/styles/kasifpl.css";
```

Update your `tsconfig.json` paths only if you don't already have `@/*` → `./`. No other Next config changes are needed.

---

## 10. Integration example

See `examples/next-page-wiring.example.tsx` for a complete illustrative page. It shows how a host supplies:

- `selection` (`ReportSelection`) plus `availableSeasons` / `availableGameweeks`
- `onSeasonChange` / `onGameweekChange` callbacks
- A `Report` object matching the contract in `types.ts`
- An `ArchiveEntry[]` list with host-computed `href` values
- `renderLink` to inject Next.js `<Link>` into the header and archive
- Loading / unavailable / error states driven by the host's data hook

The example intentionally uses `declare function useReportSelection()` and `declare function useReport()` placeholders — replace with your existing `useSelectedReport()` provider and `api.ts` client. **No mock data, API calls, or router imports live in the pack.**

---

## Data-credibility rules honoured

- Prefers `consensus.supportCount` / `.relevantExpertCount` over legacy `consensusCount` / `expertCount`.
- `mentionCount` is displayed neutrally and is **never** added to support totals.
- Missing evidence renders as an unavailable label — never as opposition.
- `confidence` is labelled as model confidence, not expert consensus.
- Provenance types are limited to the four contract values (`support | oppose | alternative | mention`).
- Thumbnails, avatars, durations, transcript status, and expert identities are never invented.
- Source links appear only when `url` is a valid `http(s)://` URL.
- An insufficient suggested team shows `ReportUnavailableState` / `SectionUnavailableState` — never a fabricated XI.
