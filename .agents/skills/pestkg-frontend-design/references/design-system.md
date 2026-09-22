# PestKG design system

## Product posture

PestKG is an operational research evidence workspace. Optimize for scanning,
comparison, provenance, repeated filtering, and bounded graph inspection. The
current implementation and `docs/design/FRONTEND_CONCEPT_V1.1.md` are the
source of truth when this reference and the application differ.

## Tokens

Use the variables in `apps/web/src/styles/tokens.css` rather than duplicating
literal colors.

| Role | Token | Current value |
| --- | --- | --- |
| Workspace background | `--bg` | `#f3f5f4` |
| Main surface | `--surface` | `#ffffff` |
| Primary text | `--ink` | `#17201d` |
| Secondary text | `--muted` | `#64716b` |
| Borders | `--border` | `#d6ddd9` |
| Primary action | `--green` | `#1f6254` |
| Warning or blocked state | `--amber` | `#a87c2c` |
| Secondary analytical accent | `--blue` | `#3c6e97` |
| Destructive or contrast accent | `--coral` | `#b9583d` |

Keep the palette functional and mixed. Borders provide most grouping;
elevation is for menus, drawers, and overlays. Use 3-7 px radii and avoid
pill-shaped containers except for a genuine status or compact selector.

## Typography and density

- Use the existing Segoe UI Variable / Noto Sans SC stack.
- Keep letter spacing at zero and never scale type from viewport width.
- Use tabular figures for counts, dates, and comparable metrics.
- Keep headings compact inside panels; reserve the largest type for the page
  title.
- Prefer aligned rows, rules, and grids over extra containers.

## Controls and feedback

- Use Lucide icons already installed in the project.
- Give icon-only buttons an accessible name and stable square dimensions.
- Use selects for release and bounded option sets, checkboxes or toggles for
  binary choices, and labeled inputs for filters.
- Preserve the two-pixel evergreen `:focus-visible` outline.
- Ensure text, hit targets, menus, and tooltips do not overlap at 320 px width.
- Limit motion to short opacity or transform feedback and honor reduced-motion
  preferences.

## Bilingual content

Add Chinese and English strings together. Prefer established terminology in
`apps/web/src/app/i18n.ts` and nearby features. Do not translate identifiers,
release IDs, official source values, or provenance fields. Let long English
labels wrap; do not shrink text to force one line.
