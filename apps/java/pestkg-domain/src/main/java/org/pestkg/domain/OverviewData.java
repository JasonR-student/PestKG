package org.pestkg.domain;

import java.util.List;
import java.util.Map;

public record OverviewData(
        String title,
        String version,
        String publishedAt,
        String cutoff,
        String status,
        String distributionStatus,
        List<String> knownLimitations,
        String mode,
        Map<String, Object> inventory,
        Map<String, Long> nodeTypes,
        Map<String, Long> relationTypes,
        List<Map<String, Object>> coverage) {
}
