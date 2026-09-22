#!/usr/bin/env sh
set -eu

auth="${NEO4J_AUTH:?NEO4J_AUTH must be set}"
user="${auth%%/*}"
password="${auth#*/}"

cypher-shell \
  -a bolt://neo4j:7687 \
  -u "$user" \
  -p "$password" \
  -f /opt/pestkg/indexes.cypher

echo "Neo4j constraints and indexes applied."
