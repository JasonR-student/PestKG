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
import java.sql.ResultSetMetaData;
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
    private final Map<String, String> paths = new ConcurrentHashMap<>();
    private final Map<String, Boolean> usesEnriched = new ConcurrentHashMap<>();
    private final Map<String, List<Map<String, Object>>> countriesCache = new ConcurrentHashMap<>();
    private final Map<String, List<Map<String, Object>>> coverageCache = new ConcurrentHashMap<>();

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
            paths.put(context.releaseId(), p);
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
        StringBuilder sql = new StringBuilder("SELECT id, type, label_original, label_en, jurisdiction, source_record_id, source_url, properties_json FROM nodes");
        List<Object> params = new ArrayList<>();
        List<String> conditions = new ArrayList<>();
        if (query != null && !query.isBlank()) {
            String needle = likePattern(query);
            conditions.add("(label_original ILIKE ? ESCAPE '\\' OR label_en ILIKE ? ESCAPE '\\' OR id ILIKE ? ESCAPE '\\')");
            params.add(needle); params.add(needle); params.add(needle);
        }
        if (type != null && !type.isBlank()) {
            conditions.add("type = ?"); params.add(type);
        }
        if (jurisdiction != null && !jurisdiction.isBlank()) {
            conditions.add("jurisdiction = ?"); params.add(jurisdiction.toUpperCase());
        }
        if (!conditions.isEmpty()) sql.append(" WHERE ").append(String.join(" AND ", conditions));
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
        ensureEnrichedUses(context, con);
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

    public List<Map<String, String>> comparison(ReleaseContext context, String question, String query, String jurisdiction, int limit) {
        if (!question.matches("q[1-5]")) {
            throw new ReleaseException("comparison_not_found", "Unknown comparison question", 404, Map.of("question", question));
        }
        boolean hasJurisdiction = jurisdiction != null && !jurisdiction.isBlank();
        boolean hasQuery = query != null && !query.isBlank();
        connection(context); // ensure the release connection (and parquet path) is initialized
        StringBuilder sql = comparisonSql(context, question, hasJurisdiction, hasQuery);
        List<Object> params = new ArrayList<>();
        if (hasJurisdiction) params.add(jurisdiction.toUpperCase());
        if (hasQuery) { String needle = likePattern(query); params.add(needle); params.add(needle); }
        params.add(Math.max(1, Math.min(limit, 500)));
        List<Map<String, String>> rows = new ArrayList<>();
        try (PreparedStatement ps = connection(context).prepareStatement(sql.toString())) {
            bind(ps, params);
            try (ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData md = rs.getMetaData();
                while (rs.next()) {
                    Map<String, String> row = new LinkedHashMap<>();
                    for (int i = 1; i <= md.getColumnCount(); i++) {
                        String value = rs.getString(i);
                        row.put(md.getColumnLabel(i), value == null ? "" : value);
                    }
                    rows.add(row);
                }
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "comparison query failed", 503, e.getMessage());
        }
        return rows;
    }

    /** Real-data Q1-Q5 competency queries computed from kg edges + canonical uses. */
    private StringBuilder comparisonSql(ReleaseContext context, String question, boolean hasJurisdiction, boolean hasQuery) {
        String p = paths.get(context.releaseId());
        String uses = "read_parquet('" + p + "/canonical/registration_uses.parquet', hive_partitioning=true) u";
        StringBuilder sql = new StringBuilder("SELECT ");
        switch (question) {
            case "q1" -> sql.append("n_ai.label_en AS active_ingredient_label_en, n_crop.label_en AS crop_label_en, count(DISTINCT u.jurisdiction_id) AS jurisdiction_count, count(*) AS registration_use_count FROM ").append(uses)
                    .append(" JOIN edges e_crop ON e_crop.start_id = u.registration_use_id AND e_crop.predicate = 'FOR_CROP'")
                    .append(" JOIN edges e_ai ON e_ai.start_id = u.product_id AND e_ai.predicate = 'CONTAINS_ACTIVE_INGREDIENT'")
                    .append(" JOIN nodes n_crop ON e_crop.end_id = n_crop.id")
                    .append(" JOIN nodes n_ai ON e_ai.end_id = n_ai.id")
                    .append(whereClause(hasJurisdiction, hasQuery, "n_ai.label_en", "n_crop.label_en"))
                    .append(" GROUP BY 1, 2 ORDER BY registration_use_count DESC LIMIT ?");
            case "q2" -> sql.append("n_prod.label_en AS product_name, n_tgt.label_en AS target_label_en, count(DISTINCT u.jurisdiction_id) AS jurisdiction_count, count(*) AS registration_use_count FROM ").append(uses)
                    .append(" JOIN edges e_tgt ON e_tgt.start_id = u.registration_use_id AND e_tgt.predicate = 'FOR_TARGET'")
                    .append(" JOIN edges e_prod ON e_prod.start_id = u.registration_use_id AND e_prod.predicate = 'USES_PRODUCT'")
                    .append(" JOIN nodes n_prod ON e_prod.end_id = n_prod.id")
                    .append(" JOIN nodes n_tgt ON e_tgt.end_id = n_tgt.id")
                    .append(whereClause(hasJurisdiction, hasQuery, "n_prod.label_en", "n_tgt.label_en"))
                    .append(" GROUP BY 1, 2 ORDER BY registration_use_count DESC LIMIT ?");
            case "q3" -> sql.append("n_crop.label_en AS crop_label_en, n_tgt.label_en AS target_label_en, count(DISTINCT u.jurisdiction_id) AS jurisdiction_count, count(*) AS registration_use_count FROM ").append(uses)
                    .append(" JOIN edges e_crop ON e_crop.start_id = u.registration_use_id AND e_crop.predicate = 'FOR_CROP'")
                    .append(" JOIN edges e_tgt ON e_tgt.start_id = u.registration_use_id AND e_tgt.predicate = 'FOR_TARGET'")
                    .append(" JOIN nodes n_crop ON e_crop.end_id = n_crop.id")
                    .append(" JOIN nodes n_tgt ON e_tgt.end_id = n_tgt.id")
                    .append(whereClause(hasJurisdiction, hasQuery, "n_crop.label_en", "n_tgt.label_en"))
                    .append(" GROUP BY 1, 2 ORDER BY registration_use_count DESC LIMIT ?");
            case "q4" -> sql.append("n_ai.label_en AS active_ingredient_label_en, u.formulation_original AS formulation_label_en, count(DISTINCT u.product_id) AS product_count, count(*) AS registration_use_count FROM ").append(uses)
                    .append(" JOIN edges e_ai ON e_ai.start_id = u.product_id AND e_ai.predicate = 'CONTAINS_ACTIVE_INGREDIENT'")
                    .append(" JOIN nodes n_ai ON e_ai.end_id = n_ai.id")
                    .append(whereClause(hasJurisdiction, hasQuery, "n_ai.label_en", "u.formulation_original"))
                    .append(" GROUP BY 1, 2 ORDER BY product_count DESC LIMIT ?");
            case "q5" -> sql.append("n_jur.label_en AS jurisdiction, n_ai.label_en AS active_ingredient_label_en, count(*) AS registration_use_count, count(DISTINCT u.product_id) AS product_count FROM ").append(uses)
                    .append(" JOIN edges e_ai ON e_ai.start_id = u.product_id AND e_ai.predicate = 'CONTAINS_ACTIVE_INGREDIENT'")
                    .append(" JOIN nodes n_ai ON e_ai.end_id = n_ai.id")
                    .append(" JOIN nodes n_jur ON n_jur.id = u.jurisdiction_id AND n_jur.type = 'Jurisdiction'")
                    .append(whereClause(hasJurisdiction, hasQuery, "n_ai.label_en", "n_jur.label_en"))
                    .append(" GROUP BY 1, 2 ORDER BY registration_use_count DESC LIMIT ?");
            default -> throw new ReleaseException("comparison_not_found", "Unknown comparison question", 404, Map.of("question", question));
        }
        return sql;
    }

    private static String whereClause(boolean hasJurisdiction, boolean hasQuery, String labelA, String labelB) {
        StringBuilder where = new StringBuilder();
        if (hasJurisdiction) {
            where.append(" WHERE u.jurisdiction_id = (SELECT id FROM nodes WHERE type = 'Jurisdiction' AND label_en = ?)");
        }
        if (hasQuery) {
            if (where.length() == 0) where.append(" WHERE");
            else where.append(" AND");
            where.append(" (").append(labelA).append(" ILIKE ? ESCAPE '\\' OR ").append(labelB).append(" ILIKE ? ESCAPE '\\')");
        }
        return where.toString();
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
                "full".equals(mode(context)) ? coverage(context) : castMapList(release.get("coverage")));
        } catch (Exception e) {
            throw new ReleaseException("dataset_unavailable", "overview failed", 503, e.getMessage());
        }
    }

    public List<Map<String, Object>> countries(ReleaseContext context) {
        if ("full".equals(mode(context))) {
            return countriesCache.computeIfAbsent(context.releaseId(), id -> derivedCountries(context));
        }
        return legacyCountries(context);
    }

    /** Full projection derived from Jurisdiction nodes and live kg counts (v1 layout). */
    private List<Map<String, Object>> derivedCountries(ReleaseContext context) {
        Connection con = connection(context);
        Map<String, Long> nodeCounts;
        Map<String, Long> edgeCounts;
        Map<String, String> codes = new LinkedHashMap<>();
        try {
            nodeCounts = groupCounts(con, "SELECT jurisdiction, count(*) FROM nodes WHERE jurisdiction IS NOT NULL AND jurisdiction <> '' GROUP BY jurisdiction");
            edgeCounts = groupCounts(con, "SELECT n.jurisdiction, count(*) FROM edges e JOIN nodes n ON e.start_id = n.id WHERE n.jurisdiction IS NOT NULL AND n.jurisdiction <> '' GROUP BY n.jurisdiction");
            try (PreparedStatement ps = con.prepareStatement("SELECT id, label_en FROM nodes WHERE type = 'Jurisdiction'");
                 ResultSet rs = ps.executeQuery()) {
                while (rs.next()) codes.put(rs.getString(1), rs.getString(2));
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "countries derivation failed", 503, e.getMessage());
        }
        List<Map<String, Object>> result = new ArrayList<>();
        codes.entrySet().stream()
                .sorted(Map.Entry.comparingByValue())
                .forEach(entry -> result.add(countryRow(entry.getKey(), entry.getValue(), nodeCounts, edgeCounts)));
        return result;
    }

    private Map<String, Object> countryRow(String jurisdictionId, String code, Map<String, Long> nodeCounts, Map<String, Long> edgeCounts) {
        Map<String, Object> country = new LinkedHashMap<>();
        country.put("jurisdiction", code);
        country.put("jurisdiction_name", ISO_NAME.getOrDefault(code, code));
        country.put("sovereign_country", code);
        country.put("site_id", "");
        country.put("official_url", "");
        country.put("source_file", "");
        country.put("source_sha256", "");
        country.put("source_snapshot_eligible", Boolean.FALSE);
        country.put("source_rows", 0L);
        country.put("skipped_rows", 0L);
        country.put("nodes", nodeCounts.getOrDefault(jurisdictionId, 0L));
        country.put("edges", edgeCounts.getOrDefault(jurisdictionId, 0L));
        country.put("broken_edges", 0L);
        country.put("graph_scope", "SINGLE_LINEAGE");
        country.put("language", "");
        country.put("iso3", ISO3.getOrDefault(code, ""));
        country.put("map_id", String.valueOf(ISO_NUM.getOrDefault(code, -1)));
        country.put("coverage", Map.of());
        return country;
    }

    /** Legacy fallback: countries.json projection or a minimal CountryOrTerritory derivation. */
    private List<Map<String, Object>> legacyCountries(ReleaseContext context) {
        Path dir = catalog.releaseDir(context.releaseId());
        if (Files.isRegularFile(dir.resolve("countries.json"))) {
            return catalog.readCountries(context);
        }
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

    /** Per-jurisdiction label coverage computed live from kg edges + canonical uses. */
    private List<Map<String, Object>> coverage(ReleaseContext context) {
        return coverageCache.computeIfAbsent(context.releaseId(), id -> computeCoverage(context));
    }

    private List<Map<String, Object>> computeCoverage(ReleaseContext context) {
        Connection con = connection(context);
        String p = paths.get(context.releaseId());
        List<Map<String, Object>> result = new ArrayList<>();
        String sql = "SELECT n_jur.label_en AS code, count(*) AS total, " +
                "count(DISTINCT e_crop.start_id) AS with_crop, count(DISTINCT e_tgt.start_id) AS with_target, " +
                "count(DISTINCT e_ai.start_id) AS with_ai, " +
                "count(DISTINCT CASE WHEN u.formulation_original IS NOT NULL AND u.formulation_original <> '' THEN u.registration_use_id END) AS with_form " +
                "FROM read_parquet('" + p + "/canonical/registration_uses.parquet', hive_partitioning=true) u " +
                "JOIN nodes n_jur ON n_jur.id = u.jurisdiction_id AND n_jur.type = 'Jurisdiction' " +
                "LEFT JOIN edges e_crop ON e_crop.start_id = u.registration_use_id AND e_crop.predicate = 'FOR_CROP' " +
                "LEFT JOIN edges e_tgt ON e_tgt.start_id = u.registration_use_id AND e_tgt.predicate = 'FOR_TARGET' " +
                "LEFT JOIN edges e_ai ON e_ai.start_id = u.product_id AND e_ai.predicate = 'CONTAINS_ACTIVE_INGREDIENT' " +
                "GROUP BY 1 ORDER BY 1";
        try (PreparedStatement ps = con.prepareStatement(sql); ResultSet rs = ps.executeQuery()) {
            while (rs.next()) {
                String code = rs.getString("code");
                long total = rs.getLong("total");
                Map<String, Object> cov = new LinkedHashMap<>();
                cov.put("jurisdiction", code);
                cov.put("source_language", "");
                cov.put("records", total);
                cov.put("crop_source", "kg FOR_CROP edges");
                cov.put("target_source", "kg FOR_TARGET edges");
                cov.put("active_source", "kg CONTAINS_ACTIVE_INGREDIENT edges");
                cov.put("formulation_source", "canonical formulation_original");
                cov.put("crop_english_given_source", ratio(rs.getLong("with_crop"), total));
                cov.put("target_english_given_source", ratio(rs.getLong("with_target"), total));
                cov.put("active_english_given_source", ratio(rs.getLong("with_ai"), total));
                cov.put("formulation_english_given_source", ratio(rs.getLong("with_form"), total));
                result.add(cov);
            }
        } catch (SQLException e) {
            throw new ReleaseException("dataset_unavailable", "coverage computation failed", 503, e.getMessage());
        }
        return result;
    }

    private static Double ratio(long part, long total) {
        return total == 0 ? 0.0 : Math.round((part * 10000.0) / total) / 10000.0;
    }

    private static final Map<String, String> ISO_NAME = Map.ofEntries(
            Map.entry("AU", "Australia"), Map.entry("CN", "China"), Map.entry("GB", "United Kingdom"),
            Map.entry("GB-NI", "Northern Ireland (UK)"), Map.entry("HU", "Hungary"), Map.entry("IE", "Ireland"),
            Map.entry("JP", "Japan"), Map.entry("KR", "South Korea"), Map.entry("NL", "Netherlands"),
            Map.entry("NZ", "New Zealand"), Map.entry("TW", "Taiwan"), Map.entry("US", "United States"));
    private static final Map<String, Integer> ISO_NUM = Map.ofEntries(
            Map.entry("AU", 36), Map.entry("CN", 156), Map.entry("GB", 826), Map.entry("GB-NI", 826),
            Map.entry("HU", 348), Map.entry("IE", 372), Map.entry("JP", 392), Map.entry("KR", 410),
            Map.entry("NL", 528), Map.entry("NZ", 554), Map.entry("TW", 158), Map.entry("US", 840));
    private static final Map<String, String> ISO3 = Map.ofEntries(
            Map.entry("AU", "AUS"), Map.entry("CN", "CHN"), Map.entry("GB", "GBR"), Map.entry("GB-NI", "GBR"),
            Map.entry("HU", "HUN"), Map.entry("IE", "IRL"), Map.entry("JP", "JPN"), Map.entry("KR", "KOR"),
            Map.entry("NL", "NLD"), Map.entry("NZ", "NZL"), Map.entry("TW", "TWN"), Map.entry("US", "USA"));

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
            where.append("(product_label_search ILIKE ? ESCAPE '\\' OR active_ingredients_search ILIKE ? ESCAPE '\\' " +
                    "OR crops_search ILIKE ? ESCAPE '\\' OR targets_search ILIKE ? ESCAPE '\\' OR formulations_search ILIKE ? ESCAPE '\\')");
            String needle = likePattern(f.query());
            for (int i = 0; i < 5; i++) params.add(needle);
        }
    }

    private void addTextFilter(StringBuilder where, List<Object> params, String column, String value) {
        if (value != null && !value.isBlank()) {
            if (where.length() > 0) where.append(" AND ");
            where.append(column).append(" ILIKE ? ESCAPE '\\'");
            params.add(likePattern(value));
        }
    }

    /** Escapes LIKE/ILIKE wildcards so user input matches literally. */
    private static String likePattern(String value) {
        return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%";
    }

    /**
     * In full (parquet) mode the v1 registration_uses view intentionally carries empty
     * search/ref columns. On first use query we replace that view with a materialized
     * table enriched from kg nodes and edges: product labels, crop/target labels via
     * FOR_CROP/FOR_TARGET edges and active-ingredient labels via CONTAINS_ACTIVE_INGREDIENT.
     * One-time cost per process (~seconds); subsequent queries are plain indexed scans.
     */
    private void ensureEnrichedUses(ReleaseContext context, Connection con) {
        String releaseId = context.releaseId();
        if (Boolean.TRUE.equals(usesEnriched.get(releaseId))) return;
        if (!"full".equals(modes.getOrDefault(releaseId, "sample"))) return;
        String p = paths.get(releaseId);
        if (p == null) return;
        synchronized (usesEnriched) {
            if (Boolean.TRUE.equals(usesEnriched.get(releaseId))) return;
            try {
                con.createStatement().execute("DROP VIEW IF EXISTS registration_uses");
                con.createStatement().execute(enrichUsesSql(p));
                usesEnriched.put(releaseId, Boolean.TRUE);
            } catch (SQLException e) {
                try {
                    con.createStatement().execute("DROP TABLE IF EXISTS registration_uses");
                } catch (SQLException cleanup) {
                    // best-effort cleanup so a retry can rebuild
                }
                throw new ReleaseException("dataset_unavailable", "registration uses enrichment failed", 503, e.getMessage());
            }
        }
    }

    private static String enrichUsesSql(String p) {
        return "CREATE TABLE registration_uses AS " +
            "WITH crop_agg AS (" +
            "    SELECT e.start_id AS use_id, group_concat(DISTINCT n.label_original, '|') AS labels, " +
            "           to_json(list_distinct(list({'id': n.id, 'label_original': n.label_original, 'label_en': n.label_en}))) AS refs " +
            "    FROM edges e JOIN nodes n ON e.end_id = n.id " +
            "    WHERE e.predicate = 'FOR_CROP' GROUP BY e.start_id), " +
            "target_agg AS (" +
            "    SELECT e.start_id AS use_id, group_concat(DISTINCT n.label_original, '|') AS labels, " +
            "           to_json(list_distinct(list({'id': n.id, 'label_original': n.label_original, 'label_en': n.label_en}))) AS refs " +
            "    FROM edges e JOIN nodes n ON e.end_id = n.id " +
            "    WHERE e.predicate = 'FOR_TARGET' GROUP BY e.start_id), " +
            "ai_agg AS (" +
            "    SELECT e.start_id AS product_id, group_concat(DISTINCT n.label_original, '|') AS labels, " +
            "           to_json(list_distinct(list({'id': n.id, 'label_original': n.label_original, 'label_en': n.label_en}))) AS refs " +
            "    FROM edges e JOIN nodes n ON e.end_id = n.id " +
            "    WHERE e.predicate = 'CONTAINS_ACTIVE_INGREDIENT' GROUP BY e.start_id) " +
            "SELECT u.registration_use_id AS use_id, u.jurisdiction_id AS jurisdiction, u.product_id, " +
            "       coalesce(p.label_original, '') AS product_label_original, " +
            "       coalesce(p.label_en, '') AS product_label_en, " +
            "       coalesce(p.label_original, '') AS product_label_search, " +
            "       coalesce(ai.labels, '') AS active_ingredients_search, " +
            "       coalesce(c.labels, '') AS crops_search, " +
            "       coalesce(t.labels, '') AS targets_search, " +
            "       coalesce(u.formulation_original, '') AS formulations_search, " +
            "       coalesce(ai.refs, '[]') AS active_ingredients_json, " +
            "       coalesce(c.refs, '[]') AS crops_json, " +
            "       coalesce(t.refs, '[]') AS targets_json, " +
            "       '[]' AS formulations_json, " +
            "       coalesce(r.original_status, '') AS registration_status, " +
            "       u.pairing_status, " +
            "       coalesce(r.registration_date_normalized, '') AS registration_date, " +
            "       coalesce(r.expiry_date_normalized, '') AS expiry_date, " +
            "       u.source_record_id, '' AS source_url " +
            "FROM read_parquet('" + p + "/canonical/registration_uses.parquet', hive_partitioning=true) u " +
            "LEFT JOIN read_parquet('" + p + "/canonical/registrations.parquet', hive_partitioning=true) r " +
            "ON u.registration_id = r.registration_id " +
            "LEFT JOIN nodes p ON u.product_id = p.id " +
            "LEFT JOIN ai_agg ai ON u.product_id = ai.product_id " +
            "LEFT JOIN crop_agg c ON u.registration_use_id = c.use_id " +
            "LEFT JOIN target_agg t ON u.registration_use_id = t.use_id";
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
