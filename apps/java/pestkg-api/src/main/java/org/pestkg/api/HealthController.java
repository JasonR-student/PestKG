package org.pestkg.api;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    private final ReleaseCatalogService catalog;

    public HealthController(ReleaseCatalogService catalog) { this.catalog = catalog; }

    @GetMapping("/health/live")
    public Map<String, Object> live() { return Map.of("status", "ok"); }

    @GetMapping("/health/ready")
    public Map<String, Object> ready() {
        ReleaseContext context = catalog.resolve(null, null);
        return Map.of("status", "ready", "release_id", context.releaseId(), "schema_version", context.schemaVersion());
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        ReleaseContext context = catalog.resolve(null, null);
        return Map.of("status", "ok", "api_version", "1.0", "release_id", context.releaseId(),
                "schema_version", context.schemaVersion(), "available_releases", catalog.list().size());
    }
}
