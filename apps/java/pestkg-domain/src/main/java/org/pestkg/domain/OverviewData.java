package org.pestkg.domain;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * Overview payload matching the MyPestKg-Beta contract (stats/overview):
 * version + headline metrics (jurisdictions/source_records/country_nodes/
 * country_edges/shared_nodes/alignment_edges) + node_types/relation_types/coverage.
 */
public record OverviewData(
        @JsonProperty("title") String title,
        @JsonProperty("version") String version,
        @JsonProperty("published_at") String publishedAt,
        @JsonProperty("cutoff") String cutoff,
        @JsonProperty("status") String status,
        @JsonProperty("distribution_status") String distributionStatus,
        @JsonProperty("known_limitations") List<String> knownLimitations,
        @JsonProperty("mode") String mode,
        @JsonProperty("inventory") Map<String, Object> inventory,
        @JsonProperty("jurisdictions") long jurisdictions,
        @JsonProperty("source_records") long sourceRecords,
        @JsonProperty("country_nodes") long countryNodes,
        @JsonProperty("country_edges") long countryEdges,
        @JsonProperty("shared_nodes") long sharedNodes,
        @JsonProperty("alignment_edges") long alignmentEdges,
        @JsonProperty("node_types") Map<String, Long> nodeTypes,
        @JsonProperty("relation_types") Map<String, Long> relationTypes,
        @JsonProperty("coverage") List<Map<String, Object>> coverage) {
}
