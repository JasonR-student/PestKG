CREATE CONSTRAINT entity_node_id IF NOT EXISTS
FOR (n:Entity) REQUIRE n.nodeId IS UNIQUE;

CREATE INDEX entity_label_original IF NOT EXISTS
FOR (n:Entity) ON (n.labelOriginal);

CREATE INDEX entity_label_english IF NOT EXISTS
FOR (n:Entity) ON (n.labelEnglish);

CREATE INDEX entity_jurisdiction IF NOT EXISTS
FOR (n:Entity) ON (n.jurisdiction);

CREATE INDEX registration_jurisdiction IF NOT EXISTS
FOR (n:Registration) ON (n.jurisdiction);

CREATE INDEX product_jurisdiction IF NOT EXISTS
FOR (n:PesticideProduct) ON (n.jurisdiction);

CREATE INDEX active_local_english IF NOT EXISTS
FOR (n:ActiveIngredientLocal) ON (n.labelEnglish);

CREATE INDEX crop_local_english IF NOT EXISTS
FOR (n:CropLocal) ON (n.labelEnglish);

CREATE INDEX target_local_english IF NOT EXISTS
FOR (n:TargetLocal) ON (n.labelEnglish);

CREATE INDEX external_source_graph IF NOT EXISTS
FOR (n:ExternalEntity) ON (n.sourceGraph);

CREATE FULLTEXT INDEX entity_name_search IF NOT EXISTS
FOR (n:Entity) ON EACH [n.labelOriginal, n.labelEnglish];
