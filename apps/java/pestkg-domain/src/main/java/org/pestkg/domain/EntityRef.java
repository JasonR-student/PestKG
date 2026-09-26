package org.pestkg.domain;

import com.fasterxml.jackson.annotation.JsonProperty;

public record EntityRef(
        @JsonProperty("id") String id,
        @JsonProperty("label_original") String labelOriginal,
        @JsonProperty("label_en") String labelEn) {
}
