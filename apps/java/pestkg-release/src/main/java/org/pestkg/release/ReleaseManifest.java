package org.pestkg.release;

import java.util.Map;

public record ReleaseManifest(String releaseId, String schemaVersion, String packageSha256,
                              Map<String, Object> inventory, String distributionStatus) {
}
