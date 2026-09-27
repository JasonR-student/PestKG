# Independent Reference Graphs

Base release: `PestKG_A_Data_Release_v1.0`. Its seven delivered Parquet files
are unchanged. `index.json` selects a separate, read-only reference pack.
This is an internal reference resource, not a new A-Line release or a public
redistribution approval.

## Coverage

| Website | Nodes | Stored edges | Input and limitation |
| --- | ---: | ---: | --- |
| AGROVOC | 593 | 572 | Bounded official API capture; not the full vocabulary |
| ChEBI | 218,726 | 408,781 | Official OBO input, version `chebi/254` |
| BCPC | 9,525 | 7,574 | Legacy derived reference; rights and content review pending |
| EPPO | 691,532 | 685,707 | Legacy derived reference; rights and content review pending |
| FRAC | 603 | 606 | Legacy derived reference; rights and content review pending |
| HRAC | 478 | 847 | Legacy derived reference; rights and content review pending |
| IRAC | 91 | 96 | Legacy derived reference; document/page mentions, not complete ingredient coverage |

Total: 921,548 nodes and 1,104,183 stored edges. IDs are source-namespaced;
all edge endpoints belong to their own website subgraph. No approved chemical
identity bridge connects these references to regulatory records. Matching
labels alone must not create such a bridge.

The main KG is one physical graph. Its 12 jurisdiction views include `TW`
(Taiwan region). Alongside seven independent reference website views, there
are 19 logical views. The 12 official website views are alternative filters
over the same regulatory records, not 12 additional independent datasets.

## Browser

Open `/graph` and select a jurisdiction, official source or reference website.
Useful queries are `Frutor Fungicide` in `source:apvma_pubcris`, `glyphosate`
in `reference:CHEBI` and `cucumbers` in `reference:AGROVOC`.
Queries return bounded neighborhoods, never every node in the selected scope.
The scope counts describe stored data; the canvas counts describe loaded nodes
and edges. Optional dashed `FROM_SNAPSHOT` relations are provenance property
projections, not stored KG facts or chemical identity assertions.

## Reproduction

Install `tools/data-production/requirements-reference.txt`, then run:

```powershell
python tools/data-production/build_reference_graphs.py `
  --chebi-obo <official-chebi-lite.obo> `
  --legacy-root <09_reference_graphs> `
  --cache runtime/reference-inputs/agrovoc `
  --out data/reference-graphs/<new-pack-id>
```

The generator never overwrites an existing pack. Update `index.json` only
after reviewing the manifest and running the offline validation:

```powershell
python -m unittest discover -s tools/data-production/tests -v
```

The AGROVOC capture uses 11 explicit search patterns with at most ten results
each, then reads concept relationships. Unfetched relationship endpoints are
marked placeholders. Reusing the cache preserves captured responses; a new
live capture may differ. Raw inputs are not embedded in the reference pack;
the manifest records filenames or request URLs, capture metadata and SHA-256
values. Full reproduction requires the recorded inputs/cache.
