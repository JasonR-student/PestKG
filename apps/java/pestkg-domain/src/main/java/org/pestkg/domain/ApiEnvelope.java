package org.pestkg.domain;

import java.util.LinkedHashMap;
import java.util.Map;

public record ApiEnvelope<T>(
        String apiVersion,
        String releaseId,
        String schemaVersion,
        String validAt,
        String transactionAt,
        T data,
        Map<String, Object> meta,
        Map<String, String> links,
        Map<String, Object> provenance) {

    public static <T> ApiEnvelope<T> of(String releaseId, String schemaVersion, T data) {
        return new ApiEnvelope<>(
                "1.0",
                releaseId,
                schemaVersion,
                null,
                null,
                data,
                new LinkedHashMap<>(),
                new LinkedHashMap<>(),
                new LinkedHashMap<>());
    }
}
