# PestKG Data Source Matrix v0.1 — proposal evidence

**Status:** repository metadata inventory only. The original RAR failed integrity testing; no source snapshot inside it was opened or counted in this phase. `source_rows`, coverage and site IDs below come from [`countries.json`](../../data/releases/2026.08.3_federated/countries.json), not independent Phase 1 recounts. `UNKNOWN` means unverified. This matrix is not a redistribution approval.

| Jurisdiction | Site ID / source name as recorded | Declared rows | Language | Declared source format/stage | Active | Crop | Target | Formulation | License / redistribution |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| AU | `apvma_pubcris` | 18,555 | en | CSV official snapshot | 100% | 67.6% | 67.6% | 100% | UNKNOWN |
| CN | `chinapesticide_icama` | 86,978 | zh | CSV official snapshot | 100% | 92.4% | 92.4% | 100% | UNKNOWN |
| TW | `aphia_pesticide` | 291,185 | zh | CSV official snapshot | 100% | 98.6% | 98.6% | 99.4% | UNKNOWN |
| GB | `hse_pestreg_gb` | 909 | en | CSV official snapshot | 100% | 100% | 0% | 97.0% | UNKNOWN |
| GB-NI | `hse_pestreg_ni` | 731 | en | CSV official snapshot | 99.2% | 100% | 0% | 79.5% | UNKNOWN |
| HU | `nebih_authorisation` | 878 | hu | CSV official snapshot | 97.4% | 70.7% | 70.7% | 90.5% | UNKNOWN |
| IE | `dafm_pcs` | 1,279 | en | CSV official snapshot | 100% | 79.2% | 0% | 100% | UNKNOWN |
| JP | `famic_acis` | 142,010 | ja | CSV official snapshot | 100% | 100% | 97.6% | 100% | UNKNOWN |
| KR | `rda_psis` | 144,050 | ko | CSV official snapshot | 100% | 100% | 100% | 100% | UNKNOWN |
| NL | `ctgb_authorisations` | 17,131 | nl | CSV official snapshot | 98.9% | 72.8% | 98.7% | 0% | UNKNOWN |
| NZ | `nz_epa_acvm` | 59,695 | en | CSV official snapshot | 100% | 0% | 0% | 100% | UNKNOWN |
| US | `epa_ppls` | 57,782 | en | CSV official snapshot | 49.2% | 37.3% | 37.2% | 29.0% | UNKNOWN |

The 12 declared `source_rows` sum to **821,183**. The coverage columns are the metadata's field-presence measures, rounded for display. They do not certify semantic correctness. All 12 rows have a `source_file` ending in `.csv`, `source_sha256`, `official_url`, `iso3`, map ID, skipped-row count and graph node/edge counts in `countries.json`. The paths point to a different machine; the underlying files were not available independently of the RAR. Organization names, access dates, time coverage, column lists, identifiers, unit conventions and source terms of use remain **UNKNOWN**. The sample has `source_record_id` and `source_url` for registration uses, but does not resolve these unknowns.

## Jurisdiction × feature interpretation

The metadata gives evidence for active ingredient, crop, target and formulation *field coverage*. It does not provide independently verified per-source availability for product, registration, RegistrationUse, organization or regulatory status. The tracked sample contains examples of the first three plus Product, Registration and RegistrationUse, but only two sampled uses per jurisdiction. A full feature matrix must be generated from a replacement archive that passes CRC and manifest verification, then checked against source files and mapping rules. `GB` and `GB-NI` share ISO3 `GBR` but are distinct regulatory jurisdictions; a `Country` key cannot replace `Jurisdiction`.

## Processing and licensing classes

| Asset/source class | Evidence | Stage | License status |
| --- | --- | --- | --- |
| 12 official regulatory snapshots | `countries.json` lists official URL, source path/hash and site ID | Declared input snapshots; source files unverified | Terms and redistribution rights UNKNOWN |
| BCPC, ChEBI, AGROVOC, FRAC, HRAC, IRAC | [`downloads/index.json`](../../data/releases/2026.08.3_federated/downloads/index.json) names exclusions | External reference/alignment sources; underlying records unverified | Explicitly excluded pending audit; text/terms location UNKNOWN |
| Project-derived release graph | [`LICENSE-DATA`](../../LICENSE-DATA) and release metadata | Derived output | Repository states CC BY 4.0 for project-derived data; full publication still blocked by integrity and source-rights review |
| Tracked sample and Q1–Q5 tables | [`sample/`](../../data/releases/2026.08.3_federated/sample) | Bounded research sample / derived comparisons | Under project data notice; third-party field obligations need review |

Before licensing decisions, capture per source: organization, exact terms URL and snapshot, `license_found`, text location, explicit redistribution statement, commercial-use statement, access date, reviewer, and a decision record. All unreviewed decisions remain `UNKNOWN`.

### Data Source License Matrix (inventory state)

The project-level `LICENSE-DATA` is not a source-specific license text. For all 12 official snapshots, `license_found`, `license_text_location`, explicit redistribution rights and commercial-use rights remain `UNKNOWN`; the source files were not opened after the archive CRC failure. This applies individually to `apvma_pubcris` (AU), `chinapesticide_icama` (CN), `aphia_pesticide` (TW), `hse_pestreg_gb` (GB), `hse_pestreg_ni` (GB-NI), `nebih_authorisation` (HU), `dafm_pcs` (IE), `famic_acis` (JP), `rda_psis` (KR), `ctgb_authorisations` (NL), `nz_epa_acvm` (NZ), and `epa_ppls` (US). The six external reference resources BCPC, ChEBI, AGROVOC, FRAC, HRAC and IRAC are explicitly excluded pending license audit in the download index; their terms and commercial-use permissions also remain `UNKNOWN`.
