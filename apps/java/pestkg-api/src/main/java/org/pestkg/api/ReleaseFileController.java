package org.pestkg.api;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/**
 * Serves individual release-package files (kg/*.parquet, canonical/*.parquet,
 * docs/*, metadata/*, root metadata) as downloads. Path traversal is blocked by
 * normalization + containment checks against the release directory.
 */
@RestController
public class ReleaseFileController {
    private final ReleaseCatalogService catalog;

    public ReleaseFileController(ReleaseCatalogService catalog) {
        this.catalog = catalog;
    }

    @GetMapping(value = "/api/v1/releases/{releaseId}/files/{*path}")
    public ResponseEntity<Resource> file(@PathVariable String releaseId, @PathVariable String path) {
        String rel = (path != null && path.startsWith("/")) ? path.substring(1) : path;
        Path dir = catalog.releaseDir(releaseId);
        Path resolved = dir.resolve(rel).normalize();
        if (!resolved.startsWith(dir.normalize()) || !Files.isRegularFile(resolved)) {
            throw new ReleaseException("artifact_not_found", "Release file not found", 404,
                    Map.of("release_id", releaseId, "path", rel));
        }
        try {
            Resource resource = new FileSystemResource(resolved.toFile());
            return ResponseEntity.ok()
                    .header(HttpHeaders.CONTENT_DISPOSITION,
                            "attachment; filename=\"" + resolved.getFileName() + "\"")
                    .contentType(MediaType.APPLICATION_OCTET_STREAM)
                    .contentLength(Files.size(resolved))
                    .body(resource);
        } catch (IOException ex) {
            throw new ReleaseException("artifact_read_failed", "Unable to read release file", 500,
                    Map.of("release_id", releaseId, "path", rel, "message", ex.getMessage()));
        }
    }
}
