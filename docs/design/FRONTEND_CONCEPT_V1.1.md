# PestKG frontend concept v1.1

## Product posture

PestKG is a research evidence workspace, not a marketing site. The interface
prioritizes version identity, provenance, comparable counts, compact tables,
and bounded graph inspection. It must never imply that blocked data is public.

## First viewport

- Fixed 224 px navigation rail on desktop; compact top bar and drawer on mobile.
- Persistent global entity search and an explicit release selector.
- Left-aligned page title with release status, cutoff date, and data mode.
- A five-column metric rail followed by the map and country ranking, with part
  of the next analytical section visible at 1440 x 1000.
- No hero, marketing copy, decorative gradient, nested cards, or fake metrics.

## Visual system

- Background: neutral cool gray `#f3f5f4`; surface: `#ffffff`.
- Primary ink: charcoal `#17201d`; muted ink: `#65716c`.
- Functional accent: evergreen `#1f6254`; warning: ochre `#9a6815`.
- Borders organize the workspace; elevation is reserved for menus and drawers.
- Radius is 3 to 7 px. Numeric data uses tabular figures.
- Typography uses Segoe UI Variable / Noto Sans SC with no viewport-scaled type.
- Motion is limited to 140–220 ms opacity and transform feedback and respects
  `prefers-reduced-motion`.

## Component inventory

- `AppShell`: navigation, mobile drawer, global search, language, release mode.
- `ReleaseSelector`: current immutable version, active marker, blocked status.
- `QueryState`: layout-matched skeleton, inline error, and empty result state.
- `MetricRail`: unboxed count summaries separated by rules.
- `MapWorkspace`: world map plus ranked jurisdiction table.
- `FilterWorkbench`: labeled fields, applied-filter state, reset and export.
- `EvidenceTable`: selectable registration rows with official-source action.
- `GraphCanvas`: one- or two-hop bounded graph with node/edge counts.
- `ReleaseCatalog`: selected version metadata, checksums, artifacts, citation.

## Responsive behavior

- Below 900 px the rail becomes a drawer and all asymmetric grids become one
  column.
- Below 640 px the top bar keeps menu, search, and release access without text
  collision; metrics become a two-column rail with the final item spanning.
- Data tables remain tables and scroll horizontally; they are not converted to
  cards. Graph canvases retain a stable 420 px mobile height.

## Required states

- Loading uses skeleton blocks matching page structure.
- Empty results explain that no published rows match the filters.
- Errors surface the stable API error code and preserve the request context.
- A blocked release is visually and textually distinct from a ready release.
- Changing release preserves route and filters but invalidates release-bound
  queries; cursors are never reused across versions.

## Allowed first-viewport copy

- Product names from `i18n.ts`.
- Navigation labels from `i18n.ts`.
- Global search placeholder.
- Data mode and immutable release identifier.
- Overview title, one-sentence research description, status, and cutoff.
- Metric labels and map/ranking headings already present in the product.
