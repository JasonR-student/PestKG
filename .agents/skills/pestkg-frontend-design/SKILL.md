---
name: pestkg-frontend-design
description: Apply the PestKG research-workspace design system when creating or modifying its React pages, components, charts, states, or responsive behavior.
---

# PestKG Frontend Design

Preserve PestKG as a bilingual, data-dense research workspace. Extend the
existing interface instead of introducing a new visual direction.

## Work from evidence

1. Inspect the target feature, its current data shape, and adjacent components
   before editing.
2. Keep the established `app / features / shared` ownership boundaries and use
   the existing tokens and components before adding new ones.
3. Preserve the public `/api/v1` contract and use generated API types from
   `apps/web/src/shared/api/generated`.
4. Add Chinese and English copy together through the existing i18n pattern.
5. Verify loading, empty, error, blocked-release, and populated states that are
   relevant to the change.

Read the references that match the task:

- [Design system](references/design-system.md) for color, type, spacing,
  controls, and accessibility decisions.
- [Page patterns](references/page-patterns.md) for shell, overview, tables,
  filters, graph, downloads, and state behavior.
- [Quality gates](references/quality-gates.md) for desktop/mobile acceptance,
  charts, performance, and visual evidence.

## Non-negotiable boundaries

- Do not add a marketing hero, sales copy, decorative card stacks, gradient
  decoration, or fake metrics and records.
- Do not hide release identity, provenance, distribution status, request
  errors, or data limitations.
- Do not turn data tables into mobile cards. Keep them horizontally scrollable.
- Do not add animation that delays work, changes data interpretation, or ignores
  `prefers-reduced-motion`.
- Do not copy reference screenshots into this skill. Use the maintained images
  under `docs/design/` as comparison evidence.
