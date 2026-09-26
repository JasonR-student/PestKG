package org.pestkg.api;

import java.util.LinkedHashMap;
import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.springframework.stereotype.Component;

@Component
public class ApiEnvelopeFactory {
    public <T> ApiEnvelope<T> wrap(ReleaseContext context, T data) {
        return wrap(context, data, "sample");
    }

    public <T> ApiEnvelope<T> wrap(ReleaseContext context, T data, String dataMode) {
        ApiEnvelope<T> base = ApiEnvelope.of(context.releaseId(), context.schemaVersion(), data);
        Map<String, Object> meta = new LinkedHashMap<>(base.meta());
        meta.put("data_mode", dataMode);
        meta.put("release_selector", "query_or_header");
        Map<String, Object> provenance = new LinkedHashMap<>(base.provenance());
        provenance.put("release_id", context.releaseId());
        provenance.put("schema_version", context.schemaVersion());
        return new ApiEnvelope<>(base.apiVersion(), base.releaseId(), base.schemaVersion(), base.validAt(),
                base.transactionAt(), base.data(), meta, base.links(), provenance);
    }
}
