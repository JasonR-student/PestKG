// Single-site APVMA subgraph used by Figure 2.
MATCH p=(root:Entity {nodeId: $product_id})-[*1..3]-(neighbor:Entity)
WHERE all(rel IN relationships(p) WHERE type(rel) IN [
  'hasRegistration', 'hasProduct', 'hasRegistrationUse', 'usesProduct',
  'hasActiveIngredient', 'hasFormulation', 'registeredForCrop',
  'registeredForTarget', 'regulatesIn'
])
WITH p LIMIT 400
UNWIND nodes(p) AS node
UNWIND relationships(p) AS rel
RETURN collect(DISTINCT node) AS nodes, collect(DISTINCT rel) AS relationships;

// Full-release federation query. It is intentionally not run against the
// bounded country sample because that sample omits federation edges.
MATCH (local:Entity)-[alignment:exactMatch|lexicalAlignment]-(shared:Entity)
WHERE local.jurisdiction IN $jurisdictions
  AND (shared.nodeId STARTS WITH 'CHEBI:'
       OR shared.nodeId STARTS WITH 'http://aims.fao.org/aos/agrovoc/')
RETURN local, alignment, shared
ORDER BY local.jurisdiction, shared.nodeId
LIMIT $limit;

// Frozen Q1 rows loaded as a derived visualization layer. These labels and
// relationships are not additions to the canonical PestKG ontology.
MATCH (observation:PaperQ1Observation)-[:OBSERVED_IN]->(country:PaperJurisdiction)
MATCH (observation)-[:ALIGNED_ACTIVE]->(active:PaperSharedActive)
MATCH (observation)-[:ALIGNED_CROP]->(crop:PaperSharedCrop)
RETURN observation.rowNumber AS row_number,
       country.jurisdiction AS jurisdiction,
       active.nodeId AS active_shared_id,
       active.labelEnglish AS active_ingredient_label_en,
       crop.nodeId AS crop_shared_id,
       crop.labelEnglish AS crop_label_en,
       observation.registrationUseCount AS registration_use_count,
       observation.pairingStatus AS pairing_status
ORDER BY row_number;
