# PestKG figure methods

## Data scope

All plotted values are derived from frozen release `2026.08.3_federated`. The figure scripts use `release.json`, `countries.json`, the bounded node/edge sample, and `sample/comparisons/q1.csv`. No values are transcribed from the two visual reference images.

## Graph extraction

The APVMA example is centered on product `AU:PRODUCT:7feed95ebf8a4d6f19180bcc` and is bounded to three hops. In Neo4j mode the isolated database contains two explicitly separated layers:

- `PaperSample`: the released bounded country graph sample and its original predicates.
- `PaperProjection`: 200 Q1 observations and visualization-only links to jurisdiction, shared active-ingredient, and shared crop nodes.

`PaperProjection` labels and links are not additions to the canonical PestKG ontology. They reproduce a released comparison table inside Neo4j so that bipartite and projection figures can be queried consistently.

## Network construction

Figure 6 selects up to 14 ChEBI identifiers that occur in at least two of the four Q1 jurisdictions. Ranking is deterministic: jurisdiction count descending, summed registration-use count descending, then identifier ascending. Jurisdiction projection weights equal the number of selected ChEBI identifiers shared by each pair. Shared-entity projection edges require co-occurrence in at least two jurisdictions.

## Visual conventions

The figures use a white background, restrained categorical colors, thin vector strokes, and direct labels. Country-local entities are never visually merged. Dashed links to ChEBI or AGROVOC mean semantic-alignment evidence because Q1 does not retain the row-level `exactMatch` versus `lexicalAlignment` predicate.

All figures are exported as editable SVG, PDF, and 600 dpi PNG. Figure 8 is designed around a 7.2 inch (approximately 183 mm) double-column width.

## Reproduction

CSV fallback:

```powershell
.\.venv\Scripts\python.exe research\figures\generate_figures.py
.\.venv\Scripts\python.exe research\figures\generate_extended_figures.py
.\.venv\Scripts\python.exe research\figures\build_delivery_package.py
```

Neo4j and container renderer:

```powershell
docker compose -f research\figures\docker-compose.yml up --build --abort-on-container-exit renderer
```

The Docker path loads the isolated sample, renders Figures 1-8, and builds the delivery ZIP. It does not modify the production PestKG volume.
