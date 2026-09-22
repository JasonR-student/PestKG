# PestKG frontend quality gates

## Maintained visual evidence

Compare relevant work against these repository files without copying them into
the skill:

- `docs/design/final-overview-desktop.png` at 1440 x 1000.
- `docs/design/final-overview-mobile.png` at 390 x 844.
- `docs/design/final-explore-desktop.png` at 1440 x 1000.
- `docs/design/FIDELITY_LEDGER_V1.1.md` for accepted deviations and checks.

Use the final renders as fidelity evidence and the concept renders only for
intent. New pages should feel native to these working surfaces rather than
copying their exact layout without regard to content.

## Responsive acceptance

At minimum verify 1440 x 1000 desktop and 390 x 844 mobile views.

- No horizontal page overflow at 390 px; tables may scroll within their own
  wrapper.
- No overlapping labels, controls, headings, menus, legends, or graph counts.
- The mobile drawer traps neither content nor keyboard focus after it closes.
- Graph canvases keep a stable usable height, approximately 420 px on mobile.
- The first viewport identifies PestKG, the selected release, and the current
  task while leaving real analytical content visible.
- Keyboard focus order and visible focus remain coherent.

## Charts and graphs

- Import only the ECharts modules a feature uses through
  `apps/web/src/shared/charts/echarts.ts`.
- Keep Cytoscape isolated in its lazy feature chunk.
- Use the design tokens for series color and encode important distinctions with
  labels, position, or shape as well as color.
- Give charts an accessible label or nearby textual/table equivalent.
- Keep legends, axes, values, and tooltips readable in both languages.
- Do not animate large datasets or graph layouts merely for decoration.

## Verification commands

Run the focused checks for a small edit and the unified entrypoint for a broad
change:

```powershell
npm --prefix apps/web run lint
npm --prefix apps/web run test
npm --prefix apps/web run build
npm --prefix apps/web run test:e2e
.\tools\verify.ps1
```

Production JavaScript chunks must stay below 500 KiB uncompressed. For visual
or responsive changes, inspect Playwright screenshots and check console errors,
failed requests, `scrollWidth === innerWidth`, release selection, filters,
pagination, CSV export, graph interaction, downloads, and language switching as
applicable.
