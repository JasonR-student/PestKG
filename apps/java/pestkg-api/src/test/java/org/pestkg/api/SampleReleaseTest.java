package org.pestkg.api;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.pestkg.domain.EntityData;
import org.pestkg.domain.GraphData;

/**
 * Integration tests against the v1.0 manifest release via {@link DuckDbDataStore}.
 * Works relative to the module directory (../../../data/releases).
 */
class SampleReleaseTest {
    private static final String RELEASE = "PestKG_A_Data_Release_v1.0";
    private final PestKgProperties properties = properties();
    private final ReleaseCatalogService catalog = new ReleaseCatalogService(properties, new ObjectMapper());
    private final DuckDbDataStore store = new DuckDbDataStore(catalog, new ObjectMapper());

    @Test
    void resolvesV1ReleaseAndReadsOverview() {
        ReleaseContext context = catalog.resolve(null, null);
        assertEquals(RELEASE, context.releaseId());
        var overview = store.overview(context);
        assertNotNull(overview);
        assertFalse(overview.nodeTypes().isEmpty(), "node_types should be derived from parquet");
        assertFalse(overview.relationTypes().isEmpty(), "relation_types should be derived from parquet");
    }

    @Test
    void searchFindsCropTerm() {
        ReleaseContext context = catalog.resolve(null, null);
        List<EntityData> results = store.search(context, "梨", null, null, 10);
        assertFalse(results.isEmpty(), "search for 梨 should hit nodes");
        assertTrue(results.stream().anyMatch(e -> "CropTerm".equals(e.type())),
                "search for 梨 should include CropTerm nodes");
    }

    @Test
    void entityAndNeighborhood() {
        ReleaseContext context = catalog.resolve(null, null);
        List<EntityData> results = store.search(context, "梨", null, null, 1);
        String id = results.get(0).id();
        assertNotNull(store.entity(context, id));
        GraphData graph = store.neighborhood(context, id, 1, 50, 100);
        assertFalse(graph.nodes().isEmpty(), "neighborhood should return connected nodes");
    }

    @Test
    void registrationUsesPagedByCrop() {
        ReleaseContext context = catalog.resolve(null, null);
        CsvDataStore.UseQuery filter = new CsvDataStore.UseQuery(
                List.of(), null, null, null, "梨", null, null, null, null);
        DuckDbDataStore.UsesPage page = store.queryUses(context, filter, 0, 5);
        assertTrue(page.total() > 0, "crop=梨 should match registration uses");
        assertEquals(5, page.rows().size());
    }

    @Test
    void comparisonGracefullyDegrades() {
        ReleaseContext context = catalog.resolve(null, null);
        assertTrue(store.comparison(context, "q1", null, 10).isEmpty(),
                "v1.0 has no comparison CSVs; endpoint should degrade to empty");
    }

    @Test
    void countriesDerivedFromNodes() {
        ReleaseContext context = catalog.resolve(null, null);
        var countries = store.countries(context);
        assertFalse(countries.isEmpty(), "CountryOrTerritory nodes should be projected to countries");
    }

    @Test
    void cursorCannotCrossReleaseOrFilter() {
        CursorService cursors = new CursorService();
        String fingerprint = cursors.fingerprint(
                new CsvDataStore.UseQuery(List.of(), "", null, null, null, null, null, null, null));
        String cursor = cursors.encode(3, RELEASE, fingerprint);
        assertEquals(3, cursors.decode(cursor, RELEASE, fingerprint));
    }

    private static PestKgProperties properties() {
        PestKgProperties value = new PestKgProperties();
        value.setDataDir(Path.of("../../../data/releases"));
        value.setStateDir(Path.of("../../../data/state"));
        value.setDefaultRelease(RELEASE);
        return value;
    }
}
