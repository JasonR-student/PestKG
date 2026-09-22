package org.pestkg.domain;

import java.time.Instant;

public record BitemporalSlice(
        Instant validFrom,
        Instant validTo,
        Instant transactionFrom,
        Instant transactionTo,
        String timePrecision,
        String operation,
        String recordHash) {
}
