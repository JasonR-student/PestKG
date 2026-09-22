package org.pestkg.api;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

class SampleReleaseTest {
    private final PestKgProperties properties = properties();
    private final ReleaseCatalogService catalog = new ReleaseCatalogService(properties, new ObjectMapper());
    private final CsvDataStore store = new CsvDataStore(catalog, new ObjectMapper());

    @Test
    void resolvesTrackedReleaseAndReadsOverview() {
        ReleaseContext context = catalog.resolve(null, null);
        assertTrue(context.releaseId().endsWith("_federated"));
        assertNotNull(catalog.overview(context));
        assertFalse(store.dataset(context).nodes().isEmpty());
    }

    @Test
    void cursorCannotCrossReleaseOrFilter() {
        CursorService cursors = new CursorService();
        String fingerprint = cursors.fingerprint(new CsvDataStore.UseQuery(java.util.List.of(), "", null, null, null, null, null, null, null));
        String cursor = cursors.encode(3, "2026.08.3_federated", fingerprint);
        assertTrue(cursors.decode(cursor, "2026.08.3_federated", fingerprint) == 3);
    }

    private static PestKgProperties properties() {
        PestKgProperties value = new PestKgProperties();
        value.setDataDir(Path.of("data/releases"));
        value.setStateDir(Path.of("data/state"));
        value.setDefaultRelease("2026.08.3_federated");
        return value;
    }
}
