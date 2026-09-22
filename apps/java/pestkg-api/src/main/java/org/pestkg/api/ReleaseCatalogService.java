package org.pestkg.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.pestkg.domain.OverviewData;
import org.pestkg.domain.ReleaseSummary;
import org.springframework.stereotype.Service;

@Service
public class ReleaseCatalogService {
    private final PestKgProperties properties;
    private final ObjectMapper mapper;

    public ReleaseCatalogService(PestKgProperties properties, ObjectMapper mapper) {
        this.properties = properties;
        this.mapper = mapper;
    }

    public ReleaseContext resolve(String queryRelease, String headerRelease) {
        if (queryRelease != null && headerRelease != null && !queryRelease.equals(headerRelease)) {
            throw new ReleaseException("release_selector_conflict", "Query and header release selectors differ", 400,
                    Map.of("query", queryRelease, "header", headerRelease));
        }
        String selected = queryRelease != null ? queryRelease : headerRelease;
        if (selected == null || selected.isBlank()) selected = activeReleaseId();
        Path dir = releaseDir(selected);
        Map<String, Object> release = readObject(dir.resolve("release.json"));
        String schema = String.valueOf(release.getOrDefault("schema_version", "1.0"));
        return new ReleaseContext(selected, schema);
    }

    public String activeReleaseId() {
        Path active = properties.getStateDir().resolve("active-release.json");
        if (Files.isRegularFile(active)) {
            Map<String, Object> value = readObject(active);
            Object id = value.get("release_id");
            if (id != null && !String.valueOf(id).isBlank()) return String.valueOf(id);
        }
        return properties.getDefaultRelease();
    }

    public Path releaseDir(String releaseId) {
        if (!releaseId.matches("[A-Za-z0-9][A-Za-z0-9._-]{0,127}")) {
            throw new ReleaseException("release_invalid", "Invalid release identifier", 400, Map.of("release_id", releaseId));
        }
        Path dir = properties.getDataDir().resolve(releaseId).normalize();
        if (!dir.startsWith(properties.getDataDir().normalize()) || !Files.isDirectory(dir)) {
            throw new ReleaseException("release_not_found", "Release directory not found", 404, Map.of("release_id", releaseId));
        }
        for (String required : List.of("release.json", "schema.json", "countries.json")) {
            if (!Files.isRegularFile(dir.resolve(required))) {
                throw new ReleaseException("release_file_missing", "Required release file is missing", 422,
                        Map.of("release_id", releaseId, "file", required));
            }
        }
        return dir;
    }

    public List<ReleaseSummary> list() {
        try {
            if (!Files.isDirectory(properties.getDataDir())) return List.of();
            List<ReleaseSummary> result = new ArrayList<>();
            try (var stream = Files.list(properties.getDataDir())) {
                stream.filter(Files::isDirectory)
                        .filter(path -> Files.isRegularFile(path.resolve("release.json")))
                        .map(path -> summary(path.getFileName().toString()))
                        .sorted(Comparator.comparing(ReleaseSummary::releaseId).reversed())
                        .forEach(result::add);
            }
            return result;
        } catch (IOException ex) {
            throw new ReleaseException("release_catalog_unavailable", "Unable to list releases", 503, ex.getMessage());
        }
    }

    public ReleaseSummary summary(String releaseId) {
        Map<String, Object> release = readObject(releaseDir(releaseId).resolve("release.json"));
        return new ReleaseSummary(
                releaseId,
                String.valueOf(release.getOrDefault("schema_version", "1.0")),
                String.valueOf(release.getOrDefault("title", "PestKG release")),
                String.valueOf(release.getOrDefault("published_at", "")),
                String.valueOf(release.getOrDefault("cutoff", "")),
                String.valueOf(release.getOrDefault("status", "unknown")),
                String.valueOf(release.getOrDefault("distribution_status", "unknown")),
                castList(release.get("known_limitations")),
                String.valueOf(release.getOrDefault("license", "")),
                castMap(release.get("inventory")),
                castMap(release.get("integrity")),
                releaseId.equals(activeReleaseId()),
                "discovered");
    }

    public OverviewData overview(ReleaseContext context) {
        Map<String, Object> release = readObject(releaseDir(context.releaseId()).resolve("release.json"));
        return new OverviewData(
                String.valueOf(release.getOrDefault("title", "PestKG")),
                context.releaseId(),
                String.valueOf(release.getOrDefault("published_at", "")),
                String.valueOf(release.getOrDefault("cutoff", "")),
                String.valueOf(release.getOrDefault("status", "unknown")),
                String.valueOf(release.getOrDefault("distribution_status", "unknown")),
                castList(release.get("known_limitations")),
                "sample",
                castMap(release.get("inventory")),
                castLongMap(release.get("node_types")),
                castLongMap(release.get("relation_types")),
                castMapList(release.get("coverage")));
    }

    public Map<String, Object> readSchema(ReleaseContext context) {
        return readObject(releaseDir(context.releaseId()).resolve("schema.json"));
    }

    public List<Map<String, Object>> readCountries(ReleaseContext context) {
        try {
            return mapper.readValue(releaseDir(context.releaseId()).resolve("countries.json").toFile(),
                    new TypeReference<>() {});
        } catch (IOException ex) {
            throw new ReleaseException("release_json_invalid", "Unable to read countries metadata", 422, ex.getMessage());
        }
    }

    public Map<String, Object> readObject(Path path) {
        try {
            return mapper.readValue(path.toFile(), new TypeReference<>() {});
        } catch (IOException ex) {
            throw new ReleaseException("release_json_invalid", "Unable to read release metadata", 422,
                    Map.of("path", path.toString(), "message", ex.getMessage()));
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object value) {
        return value instanceof Map<?, ?> map ? (Map<String, Object>) map : new LinkedHashMap<>();
    }

    private static List<String> castList(Object value) {
        if (!(value instanceof List<?> list)) return List.of();
        return list.stream().map(String::valueOf).toList();
    }

    private static List<Map<String, Object>> castMapList(Object value) {
        if (!(value instanceof List<?> list)) return List.of();
        return list.stream().filter(item -> item instanceof Map<?, ?>)
                .map(item -> castMap(item)).toList();
    }

    private static Map<String, Long> castLongMap(Object value) {
        Map<String, Long> result = new LinkedHashMap<>();
        if (value instanceof Map<?, ?> map) {
            map.forEach((key, item) -> {
                try { result.put(String.valueOf(key), Long.parseLong(String.valueOf(item))); }
                catch (NumberFormatException ignored) { }
            });
        }
        return result;
    }
}
