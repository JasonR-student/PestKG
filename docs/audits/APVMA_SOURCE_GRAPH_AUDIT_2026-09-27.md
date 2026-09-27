# APVMA source graph audit

## Frozen Input

- Base release: `PestKG_A_Data_Release_v1.0`.
- Raw snapshot: `PESTKG_RAW_SNAPSHOT_2026-09-23`.
- Source: `apvma_pubcris`, ID `SRC_36b5fb76cbd14a4f95f68131824e2571`.
- SourceSnapshot: `SSNP_7b9a3f5854a44e568c586d6c24c8567d`.
- Source file SHA-256 recorded by the release: `58970dd0d137221dbc51d4abe7eafccc33bce51435f77e360b1e7230678433b0`.

## Observed Counts

Counts were read directly from the delivered Parquet files, not from screen labels.

| AU entity type | Unique nodes |
| --- | ---: |
| Registration | 18,555 |
| PesticideProduct | 18,555 |
| RegistrationUse | 18,555 |
| LocalActiveIngredient | 2,636 |
| CropTerm | 4,330 |
| TargetTerm | 5,461 |
| FormulationTerm | 120 |

Canonical registration and registration-use table row counts both equal their distinct ID counts (18,555 each).
TW is an independent regulatory jurisdiction: 13,219 registrations, 13,207 products and 289,449 registration uses.

## Why The Source Neighborhood Has Only Two Nodes

The stored Source node has one incident edge: `HAS_SNAPSHOT`. The business nodes preserve their source and snapshot in `source_id` and `source_snapshot_id` attributes. The original neighborhood endpoint traverses explicit edges only. It does not convert metadata properties into edges.

Therefore, the two-node visualization is the Source-to-SourceSnapshot metadata component, not a count of the AU business graph. The available release does not show disappearance of AU records. These checks do not prove upstream crawling completeness or compare with the live APVMA database; the frozen release explicitly retains an upstream-completeness limitation.

## Browser Integration

The graph browser can select `source:apvma_pubcris` or `jurisdiction:AU` and query real business nodes. Optional `FROM_SNAPSHOT` edges are marked `stored_fact=false`, `origin_kind=SOURCE_PROPERTY_PROJECTION`, and `projection=node.source_snapshot_id`. They are rendered dashed, never written into the frozen KG, and excluded when provenance projection is disabled.

The frozen seven-Parquet release and its original inventory remain unchanged. Separate reference resources do not create approved local chemical identity links.

## Reproduction

```sql
SELECT node_type, count(*)
FROM read_parquet('data/releases/PestKG_A_Data_Release_v1.0/kg/nodes.parquet')
WHERE source_id = 'SRC_36b5fb76cbd14a4f95f68131824e2571'
GROUP BY node_type;
```

Regression coverage: `GraphBrowserTest.apvmaScopeContainsBusinessRecordsAndExplicitPropertyProjection`, `GraphBrowserTest.provenanceCanBeExcludedWithoutLosingBusinessGraph`.
