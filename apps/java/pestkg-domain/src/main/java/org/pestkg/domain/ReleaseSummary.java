package org.pestkg.domain;

import java.util.List;
import java.util.Map;

public record ReleaseSummary(
        String releaseId,
        String schemaVersion,
        String title,
        String publishedAt,
        String cutoff,
        String status,
        String distributionStatus,
        List<String> knownLimitations,
        String license,
        Map<String, Object> inventory,
        Map<String, Object> integrity,
        boolean active,
        String registryStatus) {
}
