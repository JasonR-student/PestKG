package org.pestkg.api;

import java.util.List;
import org.pestkg.domain.ApiEnvelope;
import org.pestkg.domain.RegistrationUseData;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/registration-uses")
public class RegistrationUseController {
    private final ReleaseCatalogService catalog;
    private final CsvDataStore store;
    private final CursorService cursors;
    private final ApiEnvelopeFactory envelopes;

    public RegistrationUseController(ReleaseCatalogService catalog, CsvDataStore store, CursorService cursors, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.cursors = cursors;
        this.envelopes = envelopes;
    }

    @PostMapping("/query")
    public ApiEnvelope<List<RegistrationUseData>> query(@RequestBody(required = false) RegistrationUseQueryRequest request,
                                                         @RequestParam(required = false) String release,
                                                         @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        RegistrationUseQueryRequest safe = request == null ? new RegistrationUseQueryRequest(null, null, 50) : request;
        CsvDataStore.UseQuery filter = safe.toUseQuery();
        String fingerprint = cursors.fingerprint(filter);
        int offset = cursors.decode(safe.cursor(), context.releaseId(), fingerprint);
        List<RegistrationUseData> all = store.queryUses(context, filter);
        int pageSize = Math.max(1, Math.min(safe.pageSize() == null ? 50 : safe.pageSize(), 200));
        List<RegistrationUseData> rows = all.subList(Math.min(offset, all.size()), Math.min(offset + pageSize, all.size()));
        String next = offset + rows.size() < all.size() ? cursors.encode(offset + rows.size(), context.releaseId(), fingerprint) : null;
        ApiEnvelope<List<RegistrationUseData>> result = envelopes.wrap(context, rows);
        result.meta().put("total", all.size());
        result.meta().put("page_size", pageSize);
        if (next != null) result.meta().put("next_cursor", next);
        return result;
    }

    public record RegistrationUseQueryRequest(Filters filters, String cursor, Integer pageSize) {
        private CsvDataStore.UseQuery toUseQuery() {
            Filters value = filters == null ? new Filters(null, null, null, null, null, null, null, null, null) : filters;
            return new CsvDataStore.UseQuery(value.jurisdictions(), value.query(), value.product(), value.activeIngredient(),
                    value.crop(), value.target(), value.formulation(), value.registrationStatus(), value.pairingStatus());
        }
    }

    public record Filters(List<String> jurisdictions, String query, String product, String activeIngredient, String crop,
                          String target, String formulation, String registrationStatus, String pairingStatus) { }
}
