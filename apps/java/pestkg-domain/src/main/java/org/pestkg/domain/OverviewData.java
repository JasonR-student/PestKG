package org.pestkg.domain;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

public record OverviewData(
        @JsonProperty("title") String title,
        @JsonProperty("release_id") String version,
        @JsonProperty("published_at") String publishedAt,
        @JsonProperty("cutoff") String cutoff,
        @JsonProperty("status") String status,
        @JsonProperty("distribution_status") String distributionStatus,
        @JsonProperty("known_limitations") List<String> knownLimitations,
        @JsonProperty("mode") String mode,
        @JsonProperty("inventory") Map<String, Object> inventory,
        @JsonProperty("node_types") Map<String, Long> nodeTypes,
        @JsonProperty("relation_types") Map<String, Long> relationTypes,
        @JsonProperty("coverage") List<Map<String, Object>> coverage) {
}
