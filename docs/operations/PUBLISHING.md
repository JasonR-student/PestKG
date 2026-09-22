# GitHub and Zenodo publishing checklist

## Prerequisites

- Resolve every blocking item in `RELEASE_AUDIT_2026-08-28.md`.
- Replace the placeholder repository URL in `CITATION.cff`.
- Add verified creator names, affiliations and ORCID identifiers.
- Complete the redistribution-rights audit for each third-party source.

## GitHub

1. Publish the MIT-licensed code, schema, documentation, tests and tracked real-data sample.
2. Keep the source RAR, runtime release directories, full Parquet and Neo4j data out of Git history.
3. Require the `CI` workflow on the default branch.
4. Tag the reviewed code release, then create a GitHub Release containing source archives, citation metadata, checksums and the small browsing samples.
5. Link the versioned server download index for full derived data files that are too large or numerous for source control.

## Zenodo

1. Connect the final public GitHub repository to Zenodo or create a dataset deposition manually.
2. Upload only the project-derived CC BY 4.0 package, its manifest, quality report, data dictionary and citation metadata.
3. Exclude raw official snapshots and third-party source files until redistribution is explicitly permitted.
4. Reserve or mint the DOI, then add it to `CITATION.cff`, the portal Downloads page and the manuscript.
5. Verify the deposited files against `SHA256SUMS` after Zenodo processing.

GitHub and Zenodo publication require the repository owner's authenticated
accounts. This repository provides the validated artifacts and checklist but
does not claim that a DOI or online release already exists.
