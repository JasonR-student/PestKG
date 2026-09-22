package org.pestkg.domain;

import java.util.Map;

public record EdgeData(
        String id,
        String startId,
        String predicate,
        String endId,
        String jurisdiction,
        String sourceRecordId,
        String sourceUrl,
        Map<String, Object> properties) {
}
