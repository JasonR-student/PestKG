package org.pestkg.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.pestkg.domain.EdgeData;
import org.pestkg.domain.EntityData;
import org.pestkg.domain.EntityRef;
import org.pestkg.domain.GraphData;
import org.pestkg.domain.RegistrationUseData;
import org.springframework.stereotype.Service;

@Service
public class CsvDataStore {
    private final ReleaseCatalogService catalog;
    private final ObjectMapper mapper;
    private final Map<String, Dataset> cache = new ConcurrentHashMap<>();

    public CsvDataStore(ReleaseCatalogService catalog, ObjectMapper mapper) {
        this.catalog = catalog;
        this.mapper = mapper;
    }

    public List<EntityData> search(ReleaseContext context, String query, String type, String jurisdiction, int limit) {
        String needle = query == null ? "" : query.trim().toLowerCase();
        return dataset(context).nodes().stream()
                .filter(node -> needle.isBlank()
                        || contains(node.id(), needle)
                        || contains(node.labelOriginal(), needle)
                        || contains(node.labelEn(), needle))
                .filter(node -> type == null || type.isBlank() || type.equalsIgnoreCase(node.type()))
                .filter(node -> jurisdiction == null || jurisdiction.isBlank()
                        || jurisdiction.equalsIgnoreCase(node.jurisdiction()))
                .sorted((a, b) -> display(a).compareToIgnoreCase(display(b)))
                .limit(Math.max(1, Math.min(limit, 100)))
                .toList();
    }

    public EntityData entity(ReleaseContext context, String id) {
        return dataset(context).nodeById().get(id);
    }

    public GraphData neighborhood(ReleaseContext context, String nodeId, int depth, int nodeLimit, int edgeLimit) {
        Dataset data = dataset(context);
        if (!data.nodeById().containsKey(nodeId)) return new GraphData(List.of(), List.of());
        Set<String> visited = new HashSet<>();
        Set<String> frontier = new HashSet<>();
        Map<String, EdgeData> edges = new LinkedHashMap<>();
        visited.add(nodeId);
        frontier.add(nodeId);
        for (int level = 0; level < Math.min(depth, 2); level++) {
            if (frontier.isEmpty() || visited.size() >= nodeLimit || edges.size() >= edgeLimit) break;
            Set<String> next = new HashSet<>();
            for (EdgeData edge : data.edges()) {
                if (!frontier.contains(edge.startId()) && !frontier.contains(edge.endId())) continue;
                if (edges.size() >= edgeLimit) break;
                edges.put(edge.id(), edge);
                String other = frontier.contains(edge.startId()) ? edge.endId() : edge.startId();
                if (visited.size() < nodeLimit && visited.add(other)) next.add(other);
            }
            frontier = next;
        }
        return new GraphData(visited.stream().map(data.nodeById()::get).filter(java.util.Objects::nonNull).toList(),
                new ArrayList<>(edges.values()));
    }

    public GraphData shortestPath(ReleaseContext context, String startId, String endId, int maxDepth) {
        Dataset data = dataset(context);
        if (!data.nodeById().containsKey(startId) || !data.nodeById().containsKey(endId)) {
            return new GraphData(List.of(), List.of());
        }
        if (startId.equals(endId)) return new GraphData(List.of(data.nodeById().get(startId)), List.of());
        record State(String node, List<String> nodes, List<EdgeData> edges) {}
        Queue<State> queue = new ArrayDeque<>();
        Set<String> visited = new HashSet<>();
        queue.add(new State(startId, List.of(startId), List.of()));
        visited.add(startId);
        while (!queue.isEmpty()) {
            State state = queue.remove();
            if (state.edges().size() >= Math.min(maxDepth, 3)) continue;
            for (EdgeData edge : data.edges()) {
                if (!edge.startId().equals(state.node()) && !edge.endId().equals(state.node())) continue;
                String neighbor = edge.startId().equals(state.node()) ? edge.endId() : edge.startId();
                List<String> pathNodes = new ArrayList<>(state.nodes());
                pathNodes.add(neighbor);
                List<EdgeData> pathEdges = new ArrayList<>(state.edges());
                pathEdges.add(edge);
                if (neighbor.equals(endId)) {
                    return new GraphData(pathNodes.stream().map(data.nodeById()::get).filter(java.util.Objects::nonNull).toList(), pathEdges);
                }
                if (visited.add(neighbor)) queue.add(new State(neighbor, pathNodes, pathEdges));
            }
        }
        return new GraphData(List.of(), List.of());
    }

    public List<RegistrationUseData> queryUses(ReleaseContext context, UseQuery filter) {
        String needle = lower(filter.query());
        return dataset(context).uses().stream()
                .filter(row -> filter.jurisdictions().isEmpty() || filter.jurisdictions().stream().anyMatch(j -> j.equalsIgnoreCase(row.jurisdiction())))
                .filter(row -> contains(row.productLabelEn(), lower(filter.product())) || isBlank(filter.product()))
                .filter(row -> listContains(row.activeIngredients(), filter.activeIngredient()) || isBlank(filter.activeIngredient()))
                .filter(row -> listContains(row.crops(), filter.crop()) || isBlank(filter.crop()))
                .filter(row -> listContains(row.targets(), filter.target()) || isBlank(filter.target()))
                .filter(row -> listContains(row.formulations(), filter.formulation()) || isBlank(filter.formulation()))
                .filter(row -> contains(row.registrationStatus(), filter.registrationStatus()) || isBlank(filter.registrationStatus()))
                .filter(row -> contains(row.pairingStatus(), filter.pairingStatus()) || isBlank(filter.pairingStatus()))
                .filter(row -> needle.isBlank() || contains(row.productLabelEn(), needle)
                        || listContains(row.activeIngredients(), needle) || listContains(row.crops(), needle)
                        || listContains(row.targets(), needle) || listContains(row.formulations(), needle))
                .sorted((a, b) -> a.useId().compareTo(b.useId()))
                .toList();
    }

    public List<Map<String, String>> comparison(ReleaseContext context, String question, String query, int limit) {
        if (!question.matches("q[1-5]")) throw new ReleaseException("comparison_not_found", "Unknown comparison question", 404, Map.of("question", question));
        Path path = catalog.releaseDir(context.releaseId()).resolve("sample/comparisons").resolve(question + ".csv");
        if (!Files.isRegularFile(path)) return List.of();
        try (CSVParser parser = CSVParser.parse(path, StandardCharsets.UTF_8,
                CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build())) {
            List<Map<String, String>> rows = new ArrayList<>();
            for (CSVRecord record : parser) {
                Map<String, String> row = new LinkedHashMap<>();
                record.toMap().forEach(row::put);
                if (query == null || query.isBlank() || row.values().stream().anyMatch(value -> contains(value, query))) rows.add(row);
                if (rows.size() >= Math.min(limit, 500)) break;
            }
            return rows;
        } catch (IOException ex) {
            throw new ReleaseException("comparison_unavailable", "Unable to read comparison dataset", 422, ex.getMessage());
        }
    }

    public Dataset dataset(ReleaseContext context) {
        return cache.computeIfAbsent(context.releaseId(), ignored -> load(context));
    }

    private Dataset load(ReleaseContext context) {
        Path sample = catalog.releaseDir(context.releaseId()).resolve("sample");
        try {
            List<EntityData> nodes = readNodes(sample.resolve("nodes.csv"));
            List<EdgeData> edges = readEdges(sample.resolve("edges.csv"));
            List<RegistrationUseData> uses = readUses(sample.resolve("registration_uses.csv"));
            Map<String, EntityData> byId = nodes.stream().collect(Collectors.toUnmodifiableMap(EntityData::id, node -> node, (a, b) -> a));
            return new Dataset(List.copyOf(nodes), List.copyOf(edges), List.copyOf(uses), byId);
        } catch (IOException ex) {
            throw new ReleaseException("dataset_unavailable", "Unable to read release sample data", 503, ex.getMessage());
        }
    }

    private List<EntityData> readNodes(Path path) throws IOException {
        if (!Files.isRegularFile(path)) return List.of();
        try (CSVParser parser = CSVParser.parse(path, StandardCharsets.UTF_8,
                CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build())) {
            List<EntityData> result = new ArrayList<>();
            for (CSVRecord r : parser) {
                result.add(new EntityData(text(r, "id"), text(r, "type"), text(r, "label_original"), nullable(r, "label_en"),
                        text(r, "jurisdiction"), text(r, "source_record_id"), text(r, "source_url"), jsonObject(text(r, "properties_json"))));
            }
            return result;
        }
    }

    private List<EdgeData> readEdges(Path path) throws IOException {
        if (!Files.isRegularFile(path)) return List.of();
        try (CSVParser parser = CSVParser.parse(path, StandardCharsets.UTF_8,
                CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build())) {
            List<EdgeData> result = new ArrayList<>();
            for (CSVRecord r : parser) {
                result.add(new EdgeData(text(r, "id"), text(r, "start_id"), text(r, "predicate"), text(r, "end_id"),
                        text(r, "jurisdiction"), text(r, "source_record_id"), text(r, "source_url"), jsonObject(text(r, "properties_json"))));
            }
            return result;
        }
    }

    private List<RegistrationUseData> readUses(Path path) throws IOException {
        if (!Files.isRegularFile(path)) return List.of();
        try (CSVParser parser = CSVParser.parse(path, StandardCharsets.UTF_8,
                CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).build())) {
            List<RegistrationUseData> result = new ArrayList<>();
            for (CSVRecord r : parser) {
                result.add(new RegistrationUseData(text(r, "use_id"), text(r, "jurisdiction"), text(r, "product_id"),
                        text(r, "product_label_original"), nullable(r, "product_label_en"), refs(text(r, "active_ingredients_json")),
                        refs(text(r, "crops_json")), refs(text(r, "targets_json")), refs(text(r, "formulations_json")),
                        nullable(r, "registration_status"), nullable(r, "registration_date"), nullable(r, "expiry_date"),
                        text(r, "pairing_status"), text(r, "source_record_id"), text(r, "source_url")));
            }
            return result;
        }
    }

    private List<EntityRef> refs(String value) {
        if (value == null || value.isBlank()) return List.of();
        try { return mapper.readValue(value, new TypeReference<>() {}); }
        catch (IOException ignored) { return List.of(); }
    }

    private Map<String, Object> jsonObject(String value) {
        if (value == null || value.isBlank()) return Map.of();
        try { return mapper.readValue(value, new TypeReference<>() {}); }
        catch (IOException ignored) { return Map.of("raw", value); }
    }

    private static String text(CSVRecord record, String key) { return record.isMapped(key) ? record.get(key) : ""; }
    private static String nullable(CSVRecord record, String key) { String value = text(record, key); return value.isBlank() ? null : value; }
    private static boolean isBlank(String value) { return value == null || value.isBlank(); }
    private static String lower(String value) { return value == null ? "" : value.trim().toLowerCase(); }
    private static boolean contains(String value, String needle) {
        return needle == null || needle.isBlank() || (value != null && value.toLowerCase().contains(needle.toLowerCase()));
    }
    private static boolean listContains(List<EntityRef> refs, String needle) {
        if (needle == null || needle.isBlank()) return false;
        String value = needle.toLowerCase();
        return refs.stream().anyMatch(ref -> contains(ref.labelOriginal(), value) || contains(ref.labelEn(), value) || contains(ref.id(), value));
    }
    private static String display(EntityData node) { return node.labelEn() == null || node.labelEn().isBlank() ? node.labelOriginal() : node.labelEn(); }

    public record UseQuery(List<String> jurisdictions, String query, String product, String activeIngredient,
                           String crop, String target, String formulation, String registrationStatus, String pairingStatus) {
        public UseQuery {
            jurisdictions = jurisdictions == null ? List.of() : jurisdictions.stream()
                    .filter(value -> value != null && !value.isBlank())
                    .map(value -> value.trim().toUpperCase())
                    .distinct()
                    .sorted()
                    .toList();
        }
    }

    public record Dataset(List<EntityData> nodes, List<EdgeData> edges, List<RegistrationUseData> uses,
                          Map<String, EntityData> nodeById) { }
}
