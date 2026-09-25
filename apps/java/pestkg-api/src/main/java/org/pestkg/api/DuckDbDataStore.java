package org.pestkg.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.pestkg.domain.EdgeData;
import org.pestkg.domain.EntityData;
import org.pestkg.domain.EntityRef;
import org.pestkg.domain.GraphData;
import org.pestkg.domain.OverviewData;
import org.pestkg.domain.RegistrationUseData;
import org.springframework.stereotype.Service;

/**
 * DuckDB-backed data store that reads the v1.0 parquet layout (kg/ + canonical/)
 * via column-mapping views, mirroring the Python DataRepository. Also supports
 * the legacy sample-CSV layout for older releases.
 */
@Service
public class DuckDbDataStore {
    private final ReleaseCatalogService catalog;
    private final ObjectMapper mapper;
    private final Map<String, Connection> connections = new ConcurrentHashMap<>();
    private final Map<String, String> modes = new ConcurrentHashMap<>();

    public DuckDbDataStore(ReleaseCatalogService catalog, ObjectMapper mapper) {
        this.catalog = catalog;
        this.mapper = mapper;
    }

    public String mode(ReleaseContext context) {
        connection(context);
        return modes.getOrDefault(context.releaseId(), "sample");
    }

    private Connection connection(ReleaseContext context) {
        return connections.computeIfAbsent(context.releaseId(), id -> open(context));
    }

    private Connection open(ReleaseContext context) {
        try {
            Class.forName("org.duckdb.DuckDBDriver");
            Connection con = DriverManager.getConnection("jdbc:duckdb:");
            Path releaseDir = catalog.releaseDir(context.releaseId());
            String p = releaseDir.toAbsolutePath().toString().replace("\\", "/");
            boolean v1 = Files.isRegularFile(releaseDir.resolve("metadata/manifest.json"))
                    && Files.isRegularFile(releaseDir.resolve("kg/nodes.parquet"));
            if (v1) {
                createV1Views(con, p, releaseDir);
                modes.put(context.releaseId(), "full");
            } else {
                createLegacyViews(con, p);
                modes.put(context.releaseId(), "sample");
            }
            return con;
        } catch (Exception e) {
            throw new ReleaseException("dataset_unavailable", "Unable to open duckdb connection", 503, e.getMessage());
        }
    }

    private void createV1Views(Connection con, String p, Path releaseDir) throws SQLException {
        con.createStatement().execute(
            "CREATE VIEW nodes AS SELECT " +
            "node_id AS id, node_type AS type, display_label AS label_original, " +
            "display_label AS label_en, jurisdiction_id AS jurisdiction, '' AS source_record_id, " +
            "'' AS source_url, extension_properties AS properties_json " +
            "FROM read_parquet('" + p + "/kg/nodes.parquet', hive_partitioning=true)");
        con.createStatement().execute(
            "CREATE VIEW edges AS SELECT " +
            "edge_id AS id, source_id AS start_id, predicate, target_id AS end_id, " +
            "'' AS jurisdiction, source_record_id, '' AS source_url, " +
            "json_object('assertion_status', assertion_status, 'evidence_id', evidence_id, " +
            "'origin_kind', origin_kind, 'pipeline_version', pipeline_version) AS properties_json " +
            "FROM read_parquet('" + p + "/kg/edges.parquet', hive_partitioning=true)");
        Path regPath = releaseDir.resolve("canonical/registrations.parquet");
        if (Files.isRegularFile(regPath)) {
            con.createStatement().execute(
                "CREATE VIEW registration_uses AS SELECT " +
                "u.registration_use_id AS use_id, u.jurisdiction_id AS jurisdiction, u.product_id, " +
                "'' AS product_label_original, '' AS product_label_en, '' AS product_label_search, " +
                "'' AS active_ingredients_search, u.crop_original AS crops_search, " +
                "u.target_original AS targets_search, u.formulation_original AS formulations_search, " +
                "'[]' AS active_ingredients_json, '[]' AS crops_json, '[]' AS targets_json, '[]' AS formulations_json, " +
                "coalesce(r.original_status, '') AS registration_status, u.pairing_status, " +
                "coalesce(r.registration_date_normalized, '') AS registration_date, " +
                "coalesce(r.expiry_date_normalized, '') AS expiry_date, u.source_record_id, '' AS source_url " +
                "FROM read_parquet('" + p + "/canonical/registration_uses.parquet', hive_partitioning=true) u " +
                "LEFT JOIN read_parquet('" + p + "/canonical/registrations.parquet', hive_partitioning=true) r " +
                "ON u.registration_id = r.registration_id");
        } else {
            con.createStatement().execute(
                "CREATE VIEW registration_uses AS SELECT " +
                "registration_use_id AS use_id, jurisdiction_id AS jurisdiction, product_id, " +
                "'' AS product_label_original, '' AS product_label_en, '' AS product_label_search, " +
                "'' AS active_ingredients_search, crop_original AS crops_search, " +
                "target_original AS targets_search, formulation_original AS formulations_search, " +
                "'[]' AS active_ingredients_json, '[]' AS crops_json, '[]' AS targets_json, '[]' AS formulations_json, " +
                "'' AS registration_status, pairing_status, '' AS registration_date, '' AS expiry_date, " +
                "source_record_id, '' AS source_url " +
                "FROM read_parquet('" + p + "/canonical/registration_uses.parquet', hive_partitioning=true)");
        }
    }

    private void createLegacyViews(Connection con, String p) throws SQLException {
        con.createStatement().execute(
            "CREATE VIEW nodes AS SELECT * FROM read_csv_auto('" + p + "/sample/nodes.csv', header=true, all_varchar=true)");
        con.createStatement().execute(
            "CREATE VIEW edges AS SELECT * FROM read_csv_auto('" + p + "/sample/edges.csv', header=true, all_varchar=true)");
        con.createStatement().execute(
            "CREATE VIEW registration_uses AS SELECT * FROM read_csv_auto('" + p + "/sample/registration_uses.csv', header=true, all_varchar=true)");
    }

    public List<EntityData> search(ReleaseContext context, String query, String type, String jurisdiction, int limit) {
        StringBuilder sql = new StringBuilder("SELECT id, type, label_original, label_en, jurisdiction, source_record_id, source_url, properties_json FROM nodes WHERE ");
        List<Object> params = new ArrayList<>();
        boolean first = true;
        if (query != null && !query.isBlank()) {
            sql.append("(label_original ILIKE ? OR label_en ILIKE ? OR id ILIKE ?)");
            String needle = "%" + query + "%";
            params.add(needle); params.add(needle); params.add(needle);
            first = false;
        }
        if (type != null && !type.isBlank()) {
            if (!first) sql.append(" AND ");
            sql.append("type = ?"); params.add(type); first = false;
        }
        if (jurisdiction != null && !jurisdiction.isBlank()) {
            if (!first) sql.append(" AND ");
            sql.append("jurisdiction = ?"); params.add(jurisdiction.toUpperCase()); first = false;
        }
        sql.append(" ORDER BY coalesce(nullif(label_en, ''), label_original) LIMIT ?");
        params.add(Math.max(1, Math.min(limit, 100)));
        List<EntityData> result = new ArrayList<>();
        try (PreparedStatement ps = connection(context).prepareStatement(sql.toString())) {
            bind(ps, params);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) result.add(readEntity(rs));
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "search failed", 503, e.getMessage());
        }
        return result;
    }

    public EntityData entity(ReleaseContext context, String id) {
        try (PreparedStatement ps = connection(context).prepareStatement(
                "SELECT id, type, label_original, label_en, jurisdiction, source_record_id, source_url, properties_json FROM nodes WHERE id = ? LIMIT 1")) {
            ps.setString(1, id);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? readEntity(rs) : null;
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "entity failed", 503, e.getMessage());
        }
    }

    public GraphData neighborhood(ReleaseContext context, String nodeId, int depth, int nodeLimit, int edgeLimit) {
        Connection con = connection(context);
        Set<String> visited = new HashSet<>();
        Set<String> frontier = new HashSet<>();
        Map<String, EdgeData> edges = new LinkedHashMap<>();
        visited.add(nodeId);
        frontier.add(nodeId);
        for (int level = 0; level < depth; level++) {
            if (frontier.isEmpty() || visited.size() >= nodeLimit || edges.size() >= edgeLimit) break;
            List<String> ids = new ArrayList<>(frontier);
            String placeholders = String.join(",", ids.stream().map(x -> "?").toList());
            List<EdgeData> found = queryEdges(con,
                "SELECT id, start_id, predicate, end_id, jurisdiction, source_record_id, source_url, properties_json FROM edges WHERE start_id IN (" + placeholders + ") OR end_id IN (" + placeholders + ") LIMIT ?",
                concat(ids, ids, List.of(edgeLimit - edges.size())));
            Set<String> next = new HashSet<>();
            for (EdgeData e : found) {
                if (edges.size() >= edgeLimit) break;
                edges.put(e.id(), e);
                String other = frontier.contains(e.startId()) ? e.endId() : e.startId();
                if (visited.size() < nodeLimit && visited.add(other)) next.add(other);
            }
            frontier = next;
        }
        List<EntityData> nodes = fetchNodes(con, new ArrayList<>(visited));
        return new GraphData(nodes, new ArrayList<>(edges.values()));
    }

    public GraphData shortestPath(ReleaseContext context, String startId, String endId, int maxDepth) {
        if (startId.equals(endId)) {
            EntityData node = entity(context, startId);
            return new GraphData(node == null ? List.of() : List.of(node), List.of());
        }
        Connection con = connection(context);
        Map<String, String[]> parent = new HashMap<>(); // neighbor -> {anchor, edgeId, startId, predicate, endId, jurisdiction, sourceRecordId, sourceUrl, propertiesJson}
        Set<String> visited = new HashSet<>();
        Set<String> frontier = new HashSet<>();
        visited.add(startId);
        frontier.add(startId);
        for (int level = 0; level < maxDepth; level++) {
            if (frontier.isEmpty()) break;
            List<String> ids = new ArrayList<>(frontier);
            String placeholders = String.join(",", ids.stream().map(x -> "?").toList());
            List<EdgeData> found = queryEdges(con,
                "SELECT id, start_id, predicate, end_id, jurisdiction, source_record_id, source_url, properties_json FROM edges WHERE start_id IN (" + placeholders + ") OR end_id IN (" + placeholders + ")",
                concat(ids, ids, List.of()));
            Set<String> next = new HashSet<>();
            boolean foundTarget = false;
            for (EdgeData e : found) {
                String start = e.startId();
                String end = e.endId();
                String neighbor, anchor;
                if (frontier.contains(start)) { neighbor = end; anchor = start; }
                else if (frontier.contains(end)) { neighbor = start; anchor = end; }
                else continue;
                if (visited.contains(neighbor)) continue;
                visited.add(neighbor);
                parent.put(neighbor, new String[]{anchor, e.id(), e.startId(), e.predicate(), e.endId(), e.jurisdiction(), e.sourceRecordId(), e.sourceUrl(), e.properties() == null ? "{}" : toJson(e.properties())});
                if (neighbor.equals(endId)) { foundTarget = true; break; }
                next.add(neighbor);
            }
            if (foundTarget) break;
            frontier = next;
        }
        if (!parent.containsKey(endId)) return new GraphData(List.of(), List.of());
        List<String> pathNodes = new ArrayList<>();
        List<EdgeData> pathEdges = new ArrayList<>();
        String current = endId;
        pathNodes.add(endId);
        while (!current.equals(startId)) {
            String[] p = parent.get(current);
            pathNodes.add(p[0]);
            pathEdges.add(new EdgeData(p[1], p[2], p[3], p[4], p[5], p[6], p[7], parseJson(p[8], Map.class)));
            current = p[0];
        }
        java.util.Collections.reverse(pathNodes);
        java.util.Collections.reverse(pathEdges);
        List<EntityData> nodes = fetchNodes(con, pathNodes);
        Map<String, EntityData> byId = new LinkedHashMap<>();
        for (EntityData n : nodes) byId.put(n.id(), n);
        List<EntityData> ordered = new ArrayList<>();
        for (String id : pathNodes) if (byId.containsKey(id)) ordered.add(byId.get(id));
        return new GraphData(ordered, pathEdges);
    }

    public UsesPage queryUses(ReleaseContext context, CsvDataStore.UseQuery filter, int offset, int limit) {
        StringBuilder where = new StringBuilder();
        List<Object> params = new ArrayList<>();
        useFilterSql(filter, where, params);
        String whereClause = where.length() == 0 ? "" : "WHERE " + where;
        Connection con = connection(context);
        int total;
        try (PreparedStatement ps = con.prepareStatement("SELECT count(*) FROM registration_uses " + whereClause)) {
            bind(ps, params);
            try (ResultSet rs = ps.executeQuery()) { rs.next(); total = rs.getInt(1); }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "uses count failed", 503, e.getMessage());
        }
        List<RegistrationUseData> rows = new ArrayList<>();
        String sql = "SELECT use_id, jurisdiction, product_id, product_label_original, product_label_en, " +
                "active_ingredients_json, crops_json, targets_json, formulations_json, " +
                "registration_status, registration_date, expiry_date, pairing_status, source_record_id, source_url " +
                "FROM registration_uses " + whereClause +
                " ORDER BY jurisdiction, use_id LIMIT ? OFFSET ?";
        try (PreparedStatement ps = con.prepareStatement(sql)) {
            List<Object> all = new ArrayList<>(params);
            all.add(limit); all.add(offset);
            bind(ps, all);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) rows.add(readUse(rs));
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "uses query failed", 503, e.getMessage());
        }
        return new UsesPage(rows, total);
    }

    public List<Map<String, String>> comparison(ReleaseContext context, String question, String query, int limit) {
        if (!question.matches("q[1-5]")) throw new ReleaseException("comparison_not_found", "Unknown comparison question", 404, Map.of("question", question));
        return List.of(); // v1.0 has no competency-question CSVs; graceful degrade
    }

    public OverviewData overview(ReleaseContext context) {
        Connection con = connection(context);
        try {
            Map<String, Long> nodeTypes = groupCounts(con, "SELECT type, count(*) FROM nodes GROUP BY type");
            Map<String, Long> relationTypes = groupCounts(con, "SELECT predicate, count(*) FROM edges GROUP BY predicate");
            Map<String, Object> release = catalog.readObject(catalog.releaseDir(context.releaseId()).resolve(
                    Files.isRegularFile(catalog.releaseDir(context.releaseId()).resolve("release.json")) ? "release.json" : "metadata/manifest.json"));
            return new OverviewData(
                String.valueOf(release.getOrDefault("title", release.getOrDefault("release_name", "PestKG"))),
                context.releaseId(),
                String.valueOf(release.getOrDefault("published_at", release.getOrDefault("created_at", ""))),
                String.valueOf(release.getOrDefault("cutoff", release.getOrDefault("raw_snapshot_id", ""))),
                String.valueOf(release.getOrDefault("status", release.getOrDefault("release_type", "unknown"))),
                String.valueOf(release.getOrDefault("distribution_status", "unknown")),
                castList(release.get("known_limitations")),
                mode(context),
                castMap(release.get("inventory")),
                nodeTypes, relationTypes,
                castMapList(release.get("coverage")));
        } catch (Exception e) {
            throw new ReleaseException("dataset_unavailable", "overview failed", 503, e.getMessage());
        }
    }

    public List<Map<String, Object>> countries(ReleaseContext context) {
        List<Map<String, Object>> result = new ArrayList<>();
        try (PreparedStatement ps = connection(context).prepareStatement(
                "SELECT id, label_original, jurisdiction FROM nodes WHERE type = 'CountryOrTerritory'")) {
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    Map<String, Object> c = new LinkedHashMap<>();
                    c.put("jurisdiction", rs.getString("jurisdiction"));
                    c.put("sovereign_country", rs.getString("label_original"));
                    c.put("map_id", rs.getString("id"));
                    result.add(c);
                }
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "countries failed", 503, e.getMessage());
        }
        return result;
    }

    // ---- helpers ----

    private void useFilterSql(CsvDataStore.UseQuery f, StringBuilder where, List<Object> params) {
        if (f.jurisdictions() != null && !f.jurisdictions().isEmpty()) {
            String ph = String.join(",", f.jurisdictions().stream().map(x -> "?").toList());
            where.append("jurisdiction IN (").append(ph).append(")");
            params.addAll(f.jurisdictions());
        }
        addTextFilter(where, params, "product_label_search", f.product());
        addTextFilter(where, params, "active_ingredients_search", f.activeIngredient());
        addTextFilter(where, params, "crops_search", f.crop());
        addTextFilter(where, params, "targets_search", f.target());
        addTextFilter(where, params, "formulations_search", f.formulation());
        addTextFilter(where, params, "registration_status", f.registrationStatus());
        addTextFilter(where, params, "pairing_status", f.pairingStatus());
        if (f.query() != null && !f.query().isBlank()) {
            if (where.length() > 0) where.append(" AND ");
            where.append("(product_label_search ILIKE ? OR active_ingredients_search ILIKE ? OR crops_search ILIKE ? OR targets_search ILIKE ? OR formulations_search ILIKE ?)");
            String needle = "%" + f.query() + "%";
            for (int i = 0; i < 5; i++) params.add(needle);
        }
    }

    private void addTextFilter(StringBuilder where, List<Object> params, String column, String value) {
        if (value != null && !value.isBlank()) {
            if (where.length() > 0) where.append(" AND ");
            where.append(column).append(" ILIKE ?");
            params.add("%" + value + "%");
        }
    }

    private List<EdgeData> queryEdges(Connection con, String sql, List<Object> params) {
        List<EdgeData> result = new ArrayList<>();
        try (PreparedStatement ps = con.prepareStatement(sql)) {
            bind(ps, params);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) result.add(readEdge(rs));
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "edges query failed", 503, e.getMessage());
        }
        return result;
    }

    private List<EntityData> fetchNodes(Connection con, List<String> ids) {
        if (ids.isEmpty()) return List.of();
        String placeholders = String.join(",", ids.stream().map(x -> "?").toList());
        List<EntityData> result = new ArrayList<>();
        try (PreparedStatement ps = con.prepareStatement(
                "SELECT id, type, label_original, label_en, jurisdiction, source_record_id, source_url, properties_json FROM nodes WHERE id IN (" + placeholders + ")")) {
            bind(ps, ids);
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) result.add(readEntity(rs));
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "nodes fetch failed", 503, e.getMessage());
        }
        return result;
    }

    private EntityData readEntity(ResultSet rs) throws SQLException {
        return new EntityData(rs.getString("id"), rs.getString("type"), rs.getString("label_original"),
                nullable(rs, "label_en"), rs.getString("jurisdiction"), rs.getString("source_record_id"),
                rs.getString("source_url"), parseJson(rs.getString("properties_json"), Map.class));
    }

    private EdgeData readEdge(ResultSet rs) throws SQLException {
        return new EdgeData(rs.getString("id"), rs.getString("start_id"), rs.getString("predicate"),
                rs.getString("end_id"), rs.getString("jurisdiction"), rs.getString("source_record_id"),
                rs.getString("source_url"), parseJson(rs.getString("properties_json"), Map.class));
    }

    private RegistrationUseData readUse(ResultSet rs) throws SQLException {
        return new RegistrationUseData(rs.getString("use_id"), rs.getString("jurisdiction"), rs.getString("product_id"),
                rs.getString("product_label_original"), nullable(rs, "product_label_en"),
                refs(rs.getString("active_ingredients_json")), refs(rs.getString("crops_json")),
                refs(rs.getString("targets_json")), refs(rs.getString("formulations_json")),
                nullable(rs, "registration_status"), nullable(rs, "registration_date"), nullable(rs, "expiry_date"),
                rs.getString("pairing_status"), rs.getString("source_record_id"), rs.getString("source_url"));
    }

    private static String nullable(ResultSet rs, String col) throws SQLException {
        String v = rs.getString(col);
        return v == null || v.isBlank() ? null : v;
    }

    private List<EntityRef> refs(String json) {
        if (json == null || json.isBlank() || json.equals("[]")) return List.of();
        try { return mapper.readValue(json, new TypeReference<>() {}); }
        catch (IOException ignored) { return List.of(); }
    }

    @SuppressWarnings("unchecked")
    private <T> T parseJson(String value, Class<T> type) {
        if (value == null || value.isBlank()) return (T) (type == Map.class ? Map.of() : List.of());
        try { return mapper.readValue(value, type); }
        catch (IOException ignored) { return (T) (type == Map.class ? Map.of() : List.of()); }
    }

    private String toJson(Object value) {
        try { return mapper.writeValueAsString(value); } catch (Exception e) { return "{}"; }
    }

    private Map<String, Long> groupCounts(Connection con, String sql) throws SQLException {
        Map<String, Long> result = new LinkedHashMap<>();
        try (PreparedStatement ps = con.prepareStatement(sql); ResultSet rs = ps.executeQuery()) {
            while (rs.next()) result.put(rs.getString(1), rs.getLong(2));
        }
        return result;
    }

    private static void bind(PreparedStatement ps, List<?> params) throws SQLException {
        for (int i = 0; i < params.size(); i++) ps.setObject(i + 1, params.get(i));
    }

    private static List<Object> concat(List<?>... lists) {
        List<Object> r = new ArrayList<>();
        for (List<?> l : lists) r.addAll(l);
        return r;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object value) {
        return value instanceof Map<?, ?> m ? (Map<String, Object>) m : new LinkedHashMap<>();
    }

    private static List<String> castList(Object value) {
        if (!(value instanceof List<?> l)) return List.of();
        return l.stream().map(String::valueOf).toList();
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> castMapList(Object value) {
        if (!(value instanceof List<?> l)) return List.of();
        return l.stream().filter(x -> x instanceof Map<?, ?>).map(x -> (Map<String, Object>) x).toList();
    }

    public record UsesPage(List<RegistrationUseData> rows, int total) { }
}
