# PestKG A-Line Internal Research Release — Handoff Summary

**Status:** DONE for INTERNAL_RESEARCH_RELEASE. **Public distribution:** BLOCKED_BY_RIGHTS_REVIEW. **Raw Snapshot:** PESTKG_RAW_SNAPSHOT_2026-09-23. **Approved models:** Canonical v0.2 and KG v0.2. **Registry:** v1.0.0.

## Where to start

- Project teammates: delivery/PestKG_A_Data_Release_v1.0/README.md.
- Full internal engineering release: dataset/releases/2.0.0_internal/manifest.json.
- Final technical quality report: docs/audits/PESTKG_DATA_RELEASE_V2_QUALITY_REPORT.md.
- Pipeline and resume guidance: tools/data-production/README.md.

## Result

| Metric | Count |
| --- | ---: |
| Canonical entities | 1,103,238 |
| GlobalChemical | 0 |
| Registrations | 164,249 |
| RegistrationUse | 726,840 |
| KG nodes | 1,103,238 |
| KG edges | 6,030,734 |

Clean handoff has exactly seven Parquet data files, README, three concise docs, manifest and SHA256SUMS (13 files). A20 self-check PASS. It excludes raw files, the damaged RAR, audit workspace, intermediate profiles, review tables and scripts.

No exact chemical identity was invented. Ambiguous multi-ingredient rows remain in the engineering quarantine ledger. Source rights are not cleared for public redistribution. No commit or push was made.
