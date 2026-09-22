#!/usr/bin/env sh
set -eu

if [ -d /data/databases/neo4j ]; then
  echo "Neo4j database already exists; refusing to overwrite it."
  exit 1
fi

neo4j-admin database import full neo4j \
  --nodes=/import/nodes.csv.gz \
  --relationships=/import/relationships.csv.gz

echo "Neo4j import completed. Start the database and apply /opt/pestkg/indexes.cypher."
