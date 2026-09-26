package org.pestkg.api;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.pestkg.domain.EntityData;
import org.pestkg.domain.OverviewData;
import org.pestkg.domain.ReleaseSummary;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Compatibility layer for the original MyPestKg-Beta frontend contract. The
 * frontend was not changed ("前端还用这个"); the Java backend serves both the
 * new contract (/datasets, /entities/search, /comparisons, two-phase exports)
 * and the legacy contract this controller exposes:
 *   GET  /api/v1/stats/overview | /stats/countries | /schema
 *   GET  /api/v1/search          (q, entity_type, jurisdiction, limit)
 *   GET  /api/v1/compare/{question}  (q, jurisdiction, limit)
 *   GET  /api/v1/graph/neighborhood   (node_id) | /graph/path (start_id, end_id)
 *   GET  /api/v1/releases/active
 *   GET  /api/v1/health | /health/live | /health/ready
 *   POST /api/v1/exports/registration-uses   (synchronous CSV stream)
 *   GET  /downloads/{release_id}/             (generated index.json)
 *   GET  /downloads/{release_id}/{*path}      (artifact file / index / SHA256SUMS)
 */
@RestController
public class CompatibilityController {
    /** Original synchronous export cap (mirrors settings.export_limit). */
    private static final int EXPORT_LIMIT = 100_000;

    private final ReleaseCatalogService catalog;
    private final DuckDbDataStore store;
    private final ApiEnvelopeFactory envelopes;
    private final ExportJobService jobs;

    public CompatibilityController(ReleaseCatalogService catalog, DuckDbDataStore store,
                                   ApiEnvelopeFactory envelopes, ExportJobService jobs) {
        this.catalog = catalog;
        this.store = store;
        this.envelopes = envelopes;
        this.jobs = jobs;
    }

    @GetMapping("/api/v1/stats/overview")
    public ApiEnvelope<OverviewData> overview(@RequestParam(required = false) String release,
                                              @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.overview(context), store.mode(context));
    }

    @GetMapping("/api/v1/stats/countries")
    public ApiEnvelope<List<Map<String, Object>>> countries(@RequestParam(required = false) String release,
                                                            @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.countries(context), store.mode(context));
    }

    @GetMapping("/api/v1/schema")
    public ApiEnvelope<Map<String, Object>> schema(@RequestParam(required = false) String release,
                                                   @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, catalog.readSchema(context), store.mode(context));
    }

    @GetMapping("/api/v1/search")
    public ApiEnvelope<List<EntityData>> search(@RequestParam(defaultValue = "") String q,
                                                @RequestParam(required = false) String entity_type,
                                                @RequestParam(required = false) String entityType,
                                                @RequestParam(required = false) String jurisdiction,
                                                @RequestParam(defaultValue = "50") int limit,
                                                @RequestParam(required = false) String release,
                                                @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        String type = entity_type != null ? entity_type : entityType;
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.search(context, q, type, jurisdiction, limit), store.mode(context));
    }

    @GetMapping("/api/v1/compare/{question}")
    public ApiEnvelope<List<Map<String, String>>> compare(@PathVariable String question,
                                                          @RequestParam(required = false) String q,
                                                          @RequestParam(required = false) String jurisdiction,
                                                          @RequestParam(defaultValue = "100") int limit,
                                                          @RequestParam(required = false) String release,
                                                          @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.comparison(context, question, q, jurisdiction, limit), store.mode(context));
    }

    @GetMapping("/api/v1/releases/active")
    public ApiEnvelope<ReleaseSummary> activeRelease() {
        ReleaseContext context = catalog.resolve(null, null);
        return envelopes.wrap(context, catalog.summary(context.releaseId()));
    }

    @GetMapping({"/api/v1/health", "/api/v1/health/live"})
    public Map<String, Object> health() {
        return Map.of("status", "ok");
    }

    @GetMapping("/api/v1/health/ready")
    public Map<String, Object> ready() {
        ReleaseContext context = catalog.resolve(null, null);
        return Map.of("status", "ready", "release_id", context.releaseId(), "schema_version", context.schemaVersion());
    }

    @PostMapping("/api/v1/exports/registration-uses")
    public ResponseEntity<Resource> exportRegistrationUses(
            @RequestBody(required = false) RegistrationUseController.RegistrationUseQueryRequest request,
            @RequestParam(required = false) String release,
            @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        RegistrationUseController.RegistrationUseQueryRequest safe = request == null
                ? new RegistrationUseController.RegistrationUseQueryRequest(null, null, 200)
                : request;
        var rows = store.queryUses(context, safe.toUseQuery(), 0, EXPORT_LIMIT + 1).rows();
        if (rows.size() > EXPORT_LIMIT) {
            throw new ReleaseException("export_too_large", "Export exceeds the synchronous row limit", 422,
                    Map.of("total", rows.size(), "limit", EXPORT_LIMIT,
                            "download_url", "/downloads/" + context.releaseId() + "/"));
        }
        var job = jobs.create(context, rows);
        Resource resource = new FileSystemResource(job.file());
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"registration-uses-" + context.releaseId() + ".csv\"")
                .header("X-PestKG-Release", context.releaseId())
                .body(resource);
    }

    @GetMapping("/downloads/{releaseId}/")
    public ResponseEntity<Resource> downloadIndex(@PathVariable String releaseId) {
        byte[] body = catalog.asJson(catalog.downloadIndex(releaseId)).getBytes(StandardCharsets.UTF_8);
        return jsonResource("index.json", body, releaseId);
    }

    @GetMapping("/downloads/{releaseId}/{*path}")
    public ResponseEntity<Resource> downloadArtifact(@PathVariable String releaseId, @PathVariable String path) {
        String rel = path == null ? "" : (path.startsWith("/") ? path.substring(1) : path);
        if (rel.isBlank()) return downloadIndex(releaseId);
        if (rel.equals("index.json")) return downloadIndex(releaseId);
        if (rel.equals("SHA256SUMS")) {
            byte[] body = catalog.sha256sums(releaseId).getBytes(StandardCharsets.UTF_8);
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("text/plain; charset=UTF-8"))
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"SHA256SUMS\"")
                    .header("X-PestKG-Release", releaseId)
                    .body(new ByteArrayResource(body));
        }
        Path dir = catalog.releaseDir(releaseId);
        Path resolved = dir.resolve(rel).normalize();
        if (!resolved.startsWith(dir.normalize()) || !Files.isRegularFile(resolved)) {
            throw new ReleaseException("artifact_not_found", "Release file not found", 404,
                    Map.of("release_id", releaseId, "path", rel));
        }
        try {
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + resolved.getFileName() + "\"")
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .contentLength(Files.size(resolved))
                    .header("X-PestKG-Release", releaseId)
                    .body(new FileSystemResource(resolved.toFile()));
        } catch (java.io.IOException ex) {
            throw new ReleaseException("artifact_read_failed", "Unable to read release file", 500,
                    Map.of("release_id", releaseId, "path", rel, "message", ex.getMessage()));
        }
    }

    private static ResponseEntity<Resource> jsonResource(String filename, byte[] body, String releaseId) {
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("application/json; charset=UTF-8"))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .header("X-PestKG-Release", releaseId)
                .body(new ByteArrayResource(body));
    }
}
