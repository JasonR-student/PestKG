package org.pestkg.api;

import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.pestkg.domain.EntityData;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/entities")
public class EntityController {
    private final ReleaseCatalogService catalog;
    private final CsvDataStore store;
    private final ApiEnvelopeFactory envelopes;

    public EntityController(ReleaseCatalogService catalog, CsvDataStore store, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.envelopes = envelopes;
    }

    @GetMapping("/search")
    public ApiEnvelope<List<EntityData>> search(@RequestParam(defaultValue = "") String q,
                                                 @RequestParam(required = false) String entityType,
                                                 @RequestParam(required = false) String jurisdiction,
                                                 @RequestParam(defaultValue = "50") int limit,
                                                 @RequestParam(required = false) String release,
                                                 @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.search(context, q, entityType, jurisdiction, limit));
    }

    @GetMapping("/{entityId}")
    public ApiEnvelope<EntityData> entity(@PathVariable String entityId,
                                          @RequestParam(required = false) String release,
                                          @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        EntityData entity = store.entity(context, entityId);
        if (entity == null) throw new ReleaseException("entity_not_found", "Entity not found", 404, Map.of("entity_id", entityId));
        return envelopes.wrap(context, entity);
    }

    @GetMapping("/{entityId}/history")
    public ApiEnvelope<Map<String, Object>> history(@PathVariable String entityId,
                                                     @RequestParam(required = false) String release,
                                                     @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        if (store.entity(context, entityId) == null) throw new ReleaseException("entity_not_found", "Entity not found", 404, Map.of("entity_id", entityId));
        EntityData entity = store.entity(context, entityId);
        String snapshotDate = catalog.overview(context).cutoff();
        Map<String, Object> version = new LinkedHashMap<>();
        version.put("version_no", 1);
        version.put("operation", "asserted");
        version.put("valid_from", snapshotDate);
        version.put("valid_to", null);
        version.put("tx_from", snapshotDate);
        version.put("tx_to", null);
        version.put("time_precision", "snapshot");
        version.put("record_hash", Integer.toHexString(entity.toString().hashCode()));
        return envelopes.wrap(context, Map.of(
                "entity_id", entityId,
                "history_status", "snapshot-backed",
                "versions", List.of(version)));
    }

    @GetMapping("/{entityId}/provenance")
    public ApiEnvelope<Map<String, Object>> provenance(@PathVariable String entityId,
                                                        @RequestParam(required = false) String release,
                                                        @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        EntityData entity = store.entity(context, entityId);
        if (entity == null) throw new ReleaseException("entity_not_found", "Entity not found", 404, Map.of("entity_id", entityId));
        return envelopes.wrap(context, Map.of(
                "entity_id", entity.id(),
                "source_record_id", entity.sourceRecordId(),
                "source_url", entity.sourceUrl(),
                "release_id", context.releaseId(),
                "evidence_status", "source-record-linked"));
    }
}
