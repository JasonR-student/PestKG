# KG Schema — concise delivered v0.2

The graph is a directed projection of Canonical assertions. Candidate lexical matches never become exact identity.

## Node types

| Node type | Count | Ordinary display |
| --- | ---: | --- |
| CountryOrTerritory | 5 | LOW |
| CropTerm | 18,488 | MEDIUM |
| FormulationTerm | 518 | LOW |
| Jurisdiction | 12 | HIGH |
| LocalActiveIngredient | 10,064 | HIGH |
| PesticideProduct | 163,441 | HIGH |
| Registration | 164,249 | MEDIUM |
| RegistrationUse | 726,840 | MEDIUM |
| RegulatoryOrganization | 6 | LOW |
| Source | 12 | HIDDEN_BY_DEFAULT |
| SourceSnapshot | 12 | HIDDEN_BY_DEFAULT |
| TargetTerm | 19,591 | MEDIUM |

## Predicates

| Predicate | Direction | Count | Meaning |
| --- | --- | ---: | --- |
| CONTAINS_ACTIVE_INGREDIENT | PesticideProduct to LocalActiveIngredient | 779,319 | Product has supported source ingredient component. |
| FOR_CROP | RegistrationUse to CropTerm | 703,273 | Use statement carries source crop term. |
| FOR_TARGET | RegistrationUse to TargetTerm | 700,495 | Use statement carries source target term. |
| HAS_REGISTRATION | Jurisdiction to Registration | 819,895 | Jurisdiction governs Registration. |
| HAS_SNAPSHOT | Source to SourceSnapshot | 12 | Source has frozen SourceSnapshot. |
| HAS_USE | Registration to RegistrationUse | 726,840 | Registration owns RegistrationUse. |
| IN_TERRITORY | Jurisdiction to CountryOrTerritory | 369,679 | Jurisdiction maps to source-stated territory. |
| REGISTERS_PRODUCT | Registration to PesticideProduct | 819,087 | Registration covers PesticideProduct. |
| REGULATES | RegulatoryOrganization to Jurisdiction | 385,541 | Organization regulates jurisdiction. |
| USES_PRODUCT | RegistrationUse to PesticideProduct | 726,593 | Use statement names Product. |

GlobalChemical / LocalActiveIngredient: no exact chemical identity was approved, so GlobalChemical and EXACT_CHEMICAL_IDENTITY counts are zero. Local terms remain source-scoped.

RegistrationUse: first-class statement under Registration, carrying crop/target/dose/method/timing in one source-row context. No Cartesian product is inferred.

Every edge carries evidence_id, source_snapshot_id and source_record_id. Detailed Evidence records are in the internal release. Display clients may filter default_hidden=true and expand by jurisdiction; they must not create independent facts.
