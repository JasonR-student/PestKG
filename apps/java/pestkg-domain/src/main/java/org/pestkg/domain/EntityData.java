package org.pestkg.domain;

import java.util.Map;

public record EntityData(
        String id,
        String type,
        String labelOriginal,
        String labelEn,
        String jurisdiction,
        String sourceRecordId,
        String sourceUrl,
        Map<String, Object> properties) {
}
