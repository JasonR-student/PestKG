# PestKG page patterns

## Application shell

Keep the release selector, global entity search, navigation, data mode, and
language control available throughout the workspace. Release changes preserve
the current route and applicable filters while invalidating release-bound
queries. Never reuse a pagination cursor across releases.

Desktop uses the fixed navigation rail and compact top bar. Below 900 px the
rail becomes a drawer and asymmetric grids become one column. Below 640 px,
menu, search, and release access must remain usable without collisions.

## Page hierarchy

Use this sequence where applicable:

1. Left-aligned page heading with a concise research description.
2. Release, cutoff, status, or scope context.
3. Primary controls or comparable metrics.
4. The working surface: map, chart, table, graph, or release catalog.
5. Method, provenance, limitations, or integrity details.

Sections are unframed layout bands or single-level panels. Do not put cards
inside cards. A repeated row, release artifact, or bounded tool can be framed
when that boundary improves scanning.

## Data workflows

- **Overview:** retain the five-part metric rail, jurisdiction map, ranked
  country list, and coverage chart. Counts must represent the selected release.
- **Explore:** keep filters labeled and compact, applied filters visible, the
  evidence table horizontally scrollable, and the selected record linked to a
  bounded local graph.
- **Compare:** derive columns from real response data and keep charts secondary
  to inspectable values. State any visible row limit.
- **Entity:** show preferred bilingual labels while preserving IDs, source
  records, official URLs, and a bounded neighborhood.
- **Downloads:** make release identity, checksums, artifact size, integrity,
  license, and citation easy to inspect before download.
- **Methods:** use real research figures and schema inventories. Do not invent
  explanatory diagrams or sample data.

## Required states

- Loading skeletons follow the final layout closely enough to avoid large
  shifts.
- Empty results say that the selected release and filters returned no published
  rows and keep reset or recovery controls available.
- Errors preserve the stable API error code or useful message and request
  context when available.
- A blocked release is distinct in both text and color; never imply it is
  publicly distributable.
- Disabled controls explain state through label, nearby context, or a tooltip,
  not color alone.

## Query behavior

Use stable React Query keys containing every response-affecting value,
including release ID, filters, cursor, entity, question, and graph depth. Pass
the query `AbortSignal` into the shared API client. Preserve URL-backed filters
when the current feature already uses them.
