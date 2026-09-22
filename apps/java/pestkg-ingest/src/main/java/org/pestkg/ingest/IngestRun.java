package org.pestkg.ingest;

import java.time.Instant;

public record IngestRun(String runId, String releaseId, String pipelineVersion, Instant startedAt, Instant completedAt,
                        String status) {
}
