# PestKG frontend fidelity ledger v1.1

## Evidence

- Accepted specification: `docs/design/FRONTEND_CONCEPT_V1.1.md`.
- Concept render: `docs/design/concept-overview-v1.1-desktop.png` at 1440 x 1000.
- Final desktop render: `docs/design/final-overview-desktop.png` at 1440 x 1000.
- Final mobile render: `docs/design/final-overview-mobile.png` at 390 x 844.
- Workflow render: `docs/design/final-explore-desktop.png` at 1440 x 1000.
- Captures were produced with Playwright Chromium after `networkidle` and the
  page heading became visible, against the built Nginx/Caddy images.

## Comparison points

| Area | Concept evidence | Final evidence | Resolution |
| --- | --- | --- | --- |
| Shell | Fixed rail, search, mode, and release control | Same hierarchy; desktop-only duplicate menu and close icons were absent | Fixed CSS selector specificity |
| Copy | Existing research title, description, metric labels, and status only | No new first-viewport marketing copy; blocked status and cutoff preserved | Exact |
| Typography | Compact technical sans hierarchy and tabular data | Segoe UI Variable/Noto Sans SC, stable sizes, no viewport-scaled type | Exact |
| Palette | Cool neutral workspace, evergreen action, ochre warning | Map, selection, warning, borders, and background preserve the token system | Exact |
| Container model | Open page, metric rail, single-level panels, table and canvas | No nested cards; explore remains a table plus bounded graph canvas | Exact |
| Responsive | Drawer below 780 px, two-column metric rail, single-column analytics | 390 px render has `scrollWidth === innerWidth`; controls and text do not overlap | Verified |
| Version state | Visible immutable release and blocked distribution state | URL, selector, request header, response header, downloads, and exports share one version | Verified by Playwright and proxy smoke tests |

## Above-the-fold copy diff

No unapproved heading, badge, hero label, CTA, or explanatory marketing copy was
added. Map legend and coverage-series labels were translated into Chinese to
complete the accepted bilingual requirement.

## Intentional deviations

- The first concept render still showed desktop menu/close controls because of
  a CSS specificity defect. The final implementation removes them on desktop
  and retains them only for the mobile drawer.
- No generated hero image was used. This is an operational research workspace;
  the real map, analytical chart, graph canvas, and existing research figures
  are the primary visual evidence.

No material visual mismatch remains after the final comparison.
