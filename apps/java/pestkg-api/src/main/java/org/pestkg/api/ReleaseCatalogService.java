package org.pestkg.api;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.pestkg.domain.OverviewData;
import org.pestkg.domain.ReleaseSummary;
import org.springframework.stereotype.Service;

@Service
public class ReleaseCatalogService {
    private final PestKgProperties properties;
    private final ObjectMapper mapper;
    private final Map<String, List<Map<String, Object>>> artifactsCache = new ConcurrentHashMap<>();
    private final Map<String, String> shaCache = new ConcurrentHashMap<>();

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
        Map<String, Object> release = releaseMetadata(dir);
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
        if (!hasReleaseMarker(dir)) {
            throw new ReleaseException("release_file_missing", "Required release metadata is missing (release.json or metadata/manifest.json)", 422,
                    Map.of("release_id", releaseId));
        }
        return dir;
    }

    private static boolean hasReleaseMarker(Path dir) {
        return Files.isRegularFile(dir.resolve("release.json"))
                || Files.isRegularFile(dir.resolve("metadata/manifest.json"));
    }

    public List<ReleaseSummary> list() {
        try {
            if (!Files.isDirectory(properties.getDataDir())) return List.of();
            List<ReleaseSummary> result = new ArrayList<>();
            try (var stream = Files.list(properties.getDataDir())) {
                stream.filter(Files::isDirectory)
                        .filter(ReleaseCatalogService::hasReleaseMarker)
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
        Map<String, Object> release = releaseMetadata(releaseDir(releaseId));
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
                "discovered",
                artifacts(releaseId));
    }

    /**
     * Scans the release directory for downloadable artifacts (kg/, canonical/, docs/,
     * metadata/ and root metadata files) and attaches a checksummed entry with a
     * download URL served by the release-files endpoint. SHA-256 digests are cached
     * per release+path so only the first listing pays the hashing cost.
     */
    public List<Map<String, Object>> artifacts(String releaseId) {
        return artifactsCache.computeIfAbsent(releaseId, id -> {
            Path dir = releaseDir(id);
            List<Map<String, Object>> result = new ArrayList<>();
            try (var stream = Files.walk(dir)) {
                stream.filter(Files::isRegularFile)
                        .filter(path -> !path.startsWith(dir.resolve("sample")))
                        .sorted(Comparator.comparing(path -> dir.relativize(path).toString().replace('\\', '/')))
                        .forEach(path -> result.add(artifactEntry(dir, id, path)));
            } catch (IOException ex) {
                throw new ReleaseException("release_catalog_unavailable", "Unable to scan release artifacts", 503, ex.getMessage());
            }
            return result;
        });
    }

    private Map<String, Object> artifactEntry(Path dir, String releaseId, Path file) {
        String rel = dir.relativize(file).toString().replace('\\', '/');
        String category = rel.startsWith("kg/") ? "knowledge_graph"
                : rel.startsWith("canonical/") ? "canonical"
                : rel.startsWith("docs/") ? "docs"
                : rel.startsWith("metadata/") ? "metadata"
                : "metadata";
        Map<String, Object> entry = new LinkedHashMap<>();
        entry.put("path", rel);
        entry.put("category", category);
        entry.put("bytes", fileSize(file));
        entry.put("sha256", sha256Cached(releaseId, rel, file));
        entry.put("url", "/api/v1/releases/" + releaseId + "/files/" + rel);
        return entry;
    }

    private String sha256Cached(String releaseId, String rel, Path file) {
        return shaCache.computeIfAbsent(releaseId + "|" + rel, key -> sha256(file));
    }

    private static String sha256(Path file) {
        try (InputStream in = Files.newInputStream(file)) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] buffer = new byte[1 << 16];
            int read;
            while ((read = in.read(buffer)) > 0) digest.update(buffer, 0, read);
            return HexFormat.of().formatHex(digest.digest());
        } catch (Exception ex) {
            return "";
        }
    }

    private static long fileSize(Path file) {
        try {
            return Files.size(file);
        } catch (IOException ex) {
            return 0L;
        }
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

    private Map<String, Object> releaseMetadata(Path dir) {
        Path releaseJson = dir.resolve("release.json");
        if (Files.isRegularFile(releaseJson)) return readObject(releaseJson);
        return readObject(dir.resolve("metadata/manifest.json"));
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
