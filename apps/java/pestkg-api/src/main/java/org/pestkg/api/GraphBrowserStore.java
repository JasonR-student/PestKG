package org.pestkg.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.pestkg.domain.EdgeData;
import org.pestkg.domain.EntityData;
import org.springframework.stereotype.Service;

@Service
public class GraphBrowserStore {
    public record Query(String scope, String type, String query, Integer limit, Boolean provenance) {}
    public record Result(List<EntityData> nodes, List<EdgeData> edges, String scope,
                         long matchedNodes, int nodeLimit, boolean truncated) {}

    private final ReleaseCatalogService catalog;
    private final PestKgProperties properties;
    private final ObjectMapper mapper;
    private final Map<String, Connection> connections = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Object>> catalogs = new ConcurrentHashMap<>();

    public GraphBrowserStore(ReleaseCatalogService catalog, PestKgProperties properties, ObjectMapper mapper) {
        this.catalog = catalog;
        this.properties = properties;
        this.mapper = mapper;
    }

    private Connection connection(ReleaseContext context) {
        return connections.computeIfAbsent(context.releaseId(), id -> {
            try {
                Connection con = DriverManager.getConnection("jdbc:duckdb:");
                String base = sqlPath(catalog.releaseDir(id));
                con.createStatement().execute("CREATE VIEW jurisdictions AS SELECT node_id AS id, display_label AS code " +
                    "FROM read_parquet('" + base + "/kg/nodes.parquet') WHERE node_type='Jurisdiction'");
                con.createStatement().execute("CREATE VIEW primary_nodes AS SELECT n.node_id AS id, n.node_type AS type, " +
                    "n.display_label AS label_original, n.display_label AS label_en, coalesce(j.code, '') AS jurisdiction, " +
                    "coalesce(json_extract_string(n.extension_properties, '$.source_record_id'), '') AS source_record_id, " +
                    "coalesce(json_extract_string(n.extension_properties, '$.source_url'), '') AS source_url, " +
                    "json_merge_patch(coalesce(nullif(n.extension_properties, ''), '{}'), " +
                    "json_object('source_id', n.source_id, 'source_snapshot_id', n.source_snapshot_id, 'evidence_id', n.evidence_id)) AS properties_json, " +
                    "'jurisdiction:' || coalesce(j.code, '') AS graph_scope, n.source_id, n.source_snapshot_id " +
                    "FROM read_parquet('" + base + "/kg/nodes.parquet') n LEFT JOIN jurisdictions j ON n.jurisdiction_id=j.id");
                con.createStatement().execute("CREATE VIEW primary_edges AS SELECT edge_id AS id, source_id AS start_id, " +
                    "predicate, target_id AS end_id, '' AS jurisdiction, source_record_id, '' AS source_url, " +
                    "json_object('assertion_status', assertion_status, 'evidence_id', evidence_id, " +
                    "'source_snapshot_id', source_snapshot_id, 'origin_kind', origin_kind, 'stored_fact', true) AS properties_json, " +
                    "'' AS graph_scope FROM read_parquet('" + base + "/kg/edges.parquet')");
                Path pack = referencePack(context);
                if (pack != null) {
                    String ref = sqlPath(pack);
                    con.createStatement().execute("CREATE VIEW browser_nodes AS SELECT * FROM primary_nodes UNION ALL " +
                        "SELECT * FROM read_parquet('" + ref + "/nodes.parquet')");
                    con.createStatement().execute("CREATE VIEW browser_edges AS SELECT * FROM primary_edges UNION ALL " +
                        "SELECT * FROM read_parquet('" + ref + "/edges.parquet')");
                } else {
                    con.createStatement().execute("CREATE VIEW browser_nodes AS SELECT * FROM primary_nodes");
                    con.createStatement().execute("CREATE VIEW browser_edges AS SELECT * FROM primary_edges");
                }
                return con;
            } catch (Exception error) {
                throw new ReleaseException("graph_unavailable", "Unable to open graph browser data", 503, error.getMessage());
            }
        });
    }

    private static String sqlPath(Path path) {
        return path.toAbsolutePath().toString().replace("\\", "/").replace("'", "''");
    }

    private Path referencePack(ReleaseContext context) {
        Path root = properties.getReferenceDir().toAbsolutePath().normalize();
        if (!Files.isRegularFile(root.resolve("index.json"))) return null;
        Map<String, Object> index = catalog.readObject(root.resolve("index.json"));
        if (!context.releaseId().equals(index.get("base_release_id"))) return null;
        Path pack = root.resolve(String.valueOf(index.get("pack_path"))).normalize();
        if (!pack.startsWith(root) || !Files.isRegularFile(pack.resolve("manifest.json"))
                || !Files.isRegularFile(pack.resolve("nodes.parquet")) || !Files.isRegularFile(pack.resolve("edges.parquet"))) {
            throw new ReleaseException("reference_pack_unavailable", "Reference pack is incomplete", 503, Map.of());
        }
        if (!context.releaseId().equals(catalog.readObject(pack.resolve("manifest.json")).get("base_release_id"))) {
            throw new ReleaseException("reference_pack_mismatch", "Reference pack belongs to a different release", 409, Map.of());
        }
        return pack;
    }

    public Map<String, Object> catalog(ReleaseContext context) {
        return catalogs.computeIfAbsent(context.releaseId(), id -> {
            Connection con = connection(context);
            List<Map<String, Object>> scopes = new ArrayList<>();
            try {
                Map<String, Map<String, Long>> jurisdictionTypes = groupedCounts(con,
                    "SELECT jurisdiction,type,count(*) FROM primary_nodes WHERE jurisdiction<>'' GROUP BY 1,2");
                Map<String, Map<String, Long>> sourceTypes = groupedCounts(con,
                    "SELECT source_id,type,count(*) FROM primary_nodes WHERE source_id<>'' GROUP BY 1,2");
                Map<String, Map<String, Long>> jurisdictionRelations = groupedCounts(con,
                    "SELECT n.jurisdiction,e.predicate,count(*) FROM primary_edges e JOIN primary_nodes n ON e.start_id=n.id GROUP BY 1,2");
                Map<String, Map<String, Long>> sourceRelations = groupedCounts(con,
                    "SELECT n.source_id,e.predicate,count(*) FROM primary_edges e JOIN primary_nodes n ON e.start_id=n.id GROUP BY 1,2");
                try (PreparedStatement ps = con.prepareStatement("SELECT jurisdiction, count(*) FROM primary_nodes " +
                        "WHERE jurisdiction<>'' GROUP BY 1 ORDER BY 1"); ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        String code = rs.getString(1);
                        scopes.add(scope("jurisdiction:" + code, code, "jurisdiction", code, rs.getLong(2), Map.of(),
                            jurisdictionTypes.getOrDefault(code, Map.of()), jurisdictionRelations.getOrDefault(code, Map.of())));
                    }
                }
                try (PreparedStatement ps = con.prepareStatement("SELECT s.id,s.label_original,s.jurisdiction,count(n.id) " +
                        "FROM primary_nodes s JOIN primary_nodes n ON n.source_id=s.id WHERE s.type='Source' GROUP BY 1,2,3 ORDER BY 2");
                     ResultSet rs = ps.executeQuery()) {
                    while (rs.next()) {
                        String sourceId = rs.getString(1);
                        scopes.add(scope("source:" + rs.getString(2), rs.getString(2), "source", rs.getString(3), rs.getLong(4),
                            Map.of("source_id", sourceId, "coverage_status", "FROZEN_REGULATORY_SOURCE"),
                            sourceTypes.getOrDefault(sourceId, Map.of()), sourceRelations.getOrDefault(sourceId, Map.of())));
                    }
                }
                Path pack = referencePack(context);
                String packId = "";
                if (pack != null) {
                    Map<String, Object> manifest = catalog.readObject(pack.resolve("manifest.json"));
                    packId = String.valueOf(manifest.get("pack_id"));
                    for (Object item : (List<?>) manifest.get("sources")) {
                        @SuppressWarnings("unchecked") Map<String, Object> source = (Map<String, Object>) item;
                        Map<String, Object> row = new LinkedHashMap<>(source);
                        row.remove("inputs");
                        scopes.add(row);
                    }
                }
                return Map.of("base_release_id", id, "reference_pack_id", packId, "scopes", scopes,
                    "exact_identity_links", 0, "primary_graphs", 1);
            } catch (SQLException error) {
                throw new ReleaseException("graph_unavailable", "Graph catalog failed", 503, error.getMessage());
            }
        });
    }

    private Map<String, Object> scope(String id, String name, String kind, String jurisdiction, long nodes,
                                      Map<String, Object> metadata, Map<String, Long> types, Map<String, Long> relations) {
        Map<String, Object> row = new LinkedHashMap<>(metadata);
        row.put("id", id); row.put("name", name); row.put("kind", kind); row.put("jurisdiction", jurisdiction); row.put("nodes", nodes);
        row.put("node_types", types);
        row.put("relation_types", relations);
        row.put("edges", relations.values().stream().mapToLong(Long::longValue).sum());
        return row;
    }

    private Map<String, Map<String, Long>> groupedCounts(Connection con, String sql) throws SQLException {
        Map<String, Map<String, Long>> result = new LinkedHashMap<>();
        try (PreparedStatement ps = con.prepareStatement(sql); ResultSet rs = ps.executeQuery()) {
            while (rs.next()) result.computeIfAbsent(rs.getString(1), key -> new LinkedHashMap<>()).put(rs.getString(2), rs.getLong(3));
        }
        return result;
    }

    private String filter(String scope, String alias, List<Object> params) {
        if (scope.equals("all")) return "1=1";
        if (scope.startsWith("jurisdiction:")) {
            params.add(scope.substring(13));
            return alias + ".jurisdiction=?";
        }
        if (scope.startsWith("reference:")) {
            params.add(scope);
            return alias + ".graph_scope=?";
        }
        if (scope.startsWith("source:")) {
            params.add(scope.substring(7));
            return alias + ".source_id IN (SELECT id FROM primary_nodes WHERE type='Source' AND label_original=?)";
        }
        throw new IllegalArgumentException("Unknown graph scope");
    }

    public Result query(ReleaseContext context, Query input, String anchor) {
        String scope = input.scope() == null ? "jurisdiction:AU" : input.scope();
        @SuppressWarnings("unchecked") List<Map<String, Object>> scopes = (List<Map<String, Object>>) catalog(context).get("scopes");
        if (!scope.equals("all") && scopes.stream().noneMatch(row -> scope.equals(row.get("id")))) {
            throw new IllegalArgumentException("Unknown graph scope");
        }
        int limit = input.limit() == null ? 120 : input.limit();
        if (limit < 10 || limit > Math.min(300, properties.getGraphNodeLimit())) throw new IllegalArgumentException("limit must be between 10 and 300");
        Connection con = connection(context);
        List<Object> params = new ArrayList<>();
        String where = filter(scope, "n", params);
        boolean lineageExpansion = false;
        if (anchor != null) {
            String anchorType = "";
            try (PreparedStatement ps = statement(con, "SELECT type FROM primary_nodes WHERE id=?", List.of(anchor));
                 ResultSet rs = ps.executeQuery()) { if (rs.next()) anchorType = rs.getString(1); }
            catch (SQLException error) { throw new ReleaseException("graph_unavailable", "Graph expansion failed", 503, error.getMessage()); }
            lineageExpansion = !Boolean.FALSE.equals(input.provenance()) && (anchorType.equals("Source") || anchorType.equals("SourceSnapshot"));
            if (lineageExpansion) {
                String field = anchorType.equals("Source") ? "source_id" : "source_snapshot_id";
                where += " AND (n.id=? OR n." + field + "=?)";
                params.add(anchor); params.add(anchor);
            } else { where += " AND n.id=?"; params.add(anchor); }
        }
        else {
            if (input.type() != null && !input.type().isBlank()) { where += " AND n.type=?"; params.add(input.type()); }
            if (input.query() != null && !input.query().isBlank()) {
                where += " AND (contains(lower(n.label_original),lower(?)) OR contains(lower(n.label_en),lower(?)) OR contains(lower(n.source_record_id),lower(?)) OR contains(lower(n.id),lower(?)))";
                for (int i = 0; i < 4; i++) params.add(input.query());
            }
        }
        Map<String, EntityData> nodes = new LinkedHashMap<>();
        Map<String, EdgeData> edges = new LinkedHashMap<>();
        long matched;
        try {
            try (PreparedStatement ps = statement(con, "SELECT count(*) FROM browser_nodes n WHERE " + where, params);
                 ResultSet rs = ps.executeQuery()) { rs.next(); matched = rs.getLong(1); }
            int seedLimit = anchor != null && !lineageExpansion ? 1 : Math.max(1, Math.min(24, (limit - 4) / 6));
            String order = " ORDER BY CASE n.type WHEN 'RegistrationUse' THEN 0 WHEN 'AGROVOCConcept' THEN 0 " +
                "WHEN 'PesticideProduct' THEN 1 WHEN 'ChEBITerm' THEN 1 ELSE 2 END, n.id LIMIT ?";
            List<Object> seedParams = new ArrayList<>(params); seedParams.add(seedLimit);
            fetchNodes(con, "SELECT n.* FROM browser_nodes n WHERE " + where + order, seedParams, nodes);
            int seeds = nodes.size();
            if (!nodes.isEmpty()) {
                List<String> ids = new ArrayList<>(nodes.keySet());
                List<Object> edgeParams = new ArrayList<>(ids); edgeParams.addAll(ids); edgeParams.add(properties.getGraphEdgeLimit());
                List<EdgeData> incident = fetchEdges(con, "SELECT * FROM browser_edges WHERE start_id IN (" + placeholders(ids.size()) +
                    ") OR end_id IN (" + placeholders(ids.size()) + ") ORDER BY id LIMIT ?", edgeParams);
                Map<String, Boolean> neighbors = new LinkedHashMap<>();
                for (EdgeData edge : incident) { neighbors.put(edge.startId(), true); neighbors.put(edge.endId(), true); }
                if (!neighbors.isEmpty()) {
                List<Object> neighborParams = new ArrayList<>(neighbors.keySet());
                String neighborWhere = filter(scope, "n", neighborParams);
                neighborParams.add(limit - nodes.size());
                fetchNodes(con, "SELECT n.* FROM browser_nodes n WHERE n.id IN (" + placeholders(neighbors.size()) + ") AND " +
                    neighborWhere + " ORDER BY n.id LIMIT ?", neighborParams, nodes);
                }
                for (EdgeData edge : incident) if (nodes.containsKey(edge.startId()) && nodes.containsKey(edge.endId())) edges.put(edge.id(), edge);
            }
            if (!Boolean.FALSE.equals(input.provenance()) && !scope.startsWith("reference:")) addProvenance(con, nodes, edges, limit);
            return new Result(new ArrayList<>(nodes.values()), new ArrayList<>(edges.values()), scope, matched, limit,
                matched > seeds || nodes.size() >= limit || edges.size() >= properties.getGraphEdgeLimit());
        } catch (SQLException error) {
            throw new ReleaseException("graph_unavailable", "Graph query failed", 503, error.getMessage());
        }
    }

    private void addProvenance(Connection con, Map<String, EntityData> nodes, Map<String, EdgeData> edges, int limit) throws SQLException {
        List<EntityData> facts = new ArrayList<>(nodes.values());
        Map<String, Boolean> ids = new LinkedHashMap<>();
        for (EntityData node : facts) {
            for (String key : List.of("source_id", "source_snapshot_id")) {
                Object id = node.properties().get(key);
                if (id instanceof String value && !value.isBlank() && !nodes.containsKey(value)) ids.put(value, true);
            }
        }
        if (!ids.isEmpty() && nodes.size() < limit) {
            List<Object> params = new ArrayList<>(ids.keySet()); params.add(limit - nodes.size());
            fetchNodes(con, "SELECT * FROM browser_nodes WHERE id IN (" + placeholders(ids.size()) + ") ORDER BY id LIMIT ?", params, nodes);
        }
        for (EntityData node : facts) {
            Object snapshot = node.properties().get("source_snapshot_id");
            if (!(snapshot instanceof String id) || !nodes.containsKey(id) || id.equals(node.id()) || node.type().equals("Source")) continue;
            if (edges.size() >= properties.getGraphEdgeLimit()) break;
            String edgeId = "VIEW_" + UUID.nameUUIDFromBytes((node.id() + id).getBytes(StandardCharsets.UTF_8)).toString().replace("-", "");
            edges.put(edgeId, new EdgeData(edgeId, node.id(), "FROM_SNAPSHOT", id, node.jurisdiction(), node.sourceRecordId(), "",
                Map.of("stored_fact", false, "origin_kind", "SOURCE_PROPERTY_PROJECTION", "projection", "node.source_snapshot_id")));
        }
        List<String> sourceIds = nodes.values().stream().filter(node -> node.type().equals("Source")).map(EntityData::id).toList();
        if (!sourceIds.isEmpty()) {
            for (EdgeData edge : fetchEdges(con, "SELECT * FROM primary_edges WHERE predicate='HAS_SNAPSHOT' AND start_id IN (" +
                    placeholders(sourceIds.size()) + ")", new ArrayList<>(sourceIds))) {
                if (nodes.containsKey(edge.endId()) && edges.size() < properties.getGraphEdgeLimit()) edges.put(edge.id(), edge);
            }
        }
    }

    private static String placeholders(int count) { return String.join(",", java.util.Collections.nCopies(count, "?")); }

    private PreparedStatement statement(Connection con, String sql, List<?> params) throws SQLException {
        PreparedStatement ps = con.prepareStatement(sql);
        for (int i = 0; i < params.size(); i++) ps.setObject(i + 1, params.get(i));
        return ps;
    }

    private Map<String, Object> json(String value) {
        try { return mapper.readValue(value, new TypeReference<>() {}); }
        catch (Exception error) { throw new ReleaseException("graph_invalid_properties", "Invalid graph properties", 503, error.getMessage()); }
    }

    private void fetchNodes(Connection con, String sql, List<?> params, Map<String, EntityData> output) throws SQLException {
        try (PreparedStatement ps = statement(con, sql, params); ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                EntityData node = new EntityData(rs.getString("id"), rs.getString("type"), rs.getString("label_original"), rs.getString("label_en"),
                    rs.getString("jurisdiction"), rs.getString("source_record_id"), rs.getString("source_url"), json(rs.getString("properties_json")));
                output.put(node.id(), node);
            }
        }
    }

    private List<EdgeData> fetchEdges(Connection con, String sql, List<?> params) throws SQLException {
        List<EdgeData> output = new ArrayList<>();
        try (PreparedStatement ps = statement(con, sql, params); ResultSet rs = ps.executeQuery()) {
            while (rs.next()) output.add(new EdgeData(rs.getString("id"), rs.getString("start_id"), rs.getString("predicate"), rs.getString("end_id"),
                rs.getString("jurisdiction"), rs.getString("source_record_id"), rs.getString("source_url"), json(rs.getString("properties_json"))));
        }
        return output;
    }
}
