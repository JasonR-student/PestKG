package org.pestkg.api;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.pestkg.domain.ReleaseSummary;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/releases")
public class ReleaseController {
    private final ReleaseCatalogService catalog;
    private final ApiEnvelopeFactory envelopes;

    public ReleaseController(ReleaseCatalogService catalog, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.envelopes = envelopes;
    }

    @GetMapping
    public ApiEnvelope<List<ReleaseSummary>> list() {
        ReleaseContext context = catalog.resolve(null, null);
        return envelopes.wrap(context, catalog.list());
    }

    @GetMapping("/{releaseId}")
    public ApiEnvelope<ReleaseSummary> detail(@PathVariable String releaseId) {
        ReleaseContext context = catalog.resolve(releaseId, null);
        return envelopes.wrap(context, catalog.summary(releaseId));
    }

    @GetMapping("/{releaseId}/diff")
    public ApiEnvelope<Map<String, Object>> diff(@PathVariable String releaseId,
                                                  @RequestParam(required = false) String against,
                                                  @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(releaseId, header);
        String base = against == null || against.isBlank() ? context.releaseId() : against;
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("release_id", context.releaseId());
        data.put("against_release_id", base);
        data.put("status", context.releaseId().equals(base) ? "identity" : "comparison_pending");
        data.put("record_hash_strategy", "canonical-record-sha256");
        return envelopes.wrap(context, data);
    }
}
