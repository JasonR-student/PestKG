package org.pestkg.api;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
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
    void comparisonComputesRealQ1Rows() {
        ReleaseContext context = catalog.resolve(null, null);
        var rows = store.comparison(context, "q1", null, null, 10);
        assertFalse(rows.isEmpty(), "Q1 crop-ingredient coverage should be computed from kg edges");
        assertTrue(rows.get(0).containsKey("active_ingredient_label_en"), "Q1 rows should carry ingredient labels");
        assertTrue(rows.get(0).containsKey("registration_use_count"), "Q1 rows should carry use counts");
    }

    @Test
    void comparisonFiltersByJurisdiction() {
        ReleaseContext context = catalog.resolve(null, null);
        var rows = store.comparison(context, "q5", null, "CN", 10);
        for (var row : rows) {
            assertEquals("CN", row.get("jurisdiction"), "jurisdiction filter should restrict Q5 rows");
        }
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

    @Test
    void emptySearchDoesNotFail() {
        ReleaseContext context = catalog.resolve(null, null);
        List<EntityData> results = store.search(context, "", null, null, 10);
        assertNotNull(results, "empty search should return a list, not fail");
    }

    @Test
    void usesAreEnrichedWithProductCropAndTarget() {
        ReleaseContext context = catalog.resolve(null, null);
        CsvDataStore.UseQuery filter = new CsvDataStore.UseQuery(
                List.of(), null, null, null, "梨", null, null, null, null);
        DuckDbDataStore.UsesPage page = store.queryUses(context, filter, 0, 5);
        assertTrue(page.total() > 0, "crop=梨 should match registration uses");
        assertFalse(page.rows().isEmpty());
        boolean anyProductLabel = page.rows().stream().anyMatch(r ->
                r.productLabelOriginal() != null && !r.productLabelOriginal().isBlank());
        assertTrue(anyProductLabel, "enriched uses should carry product labels from kg nodes");
        boolean anyCropRef = page.rows().stream().anyMatch(r -> !r.crops().isEmpty());
        assertTrue(anyCropRef, "enriched uses should carry structured crop refs from FOR_CROP edges");
    }

    @Test
    void productAndActiveIngredientFiltersMatch() {
        ReleaseContext context = catalog.resolve(null, null);
        CsvDataStore.UseQuery byProduct = new CsvDataStore.UseQuery(
                List.of(), null, "甲", null, null, null, null, null, null);
        assertTrue(store.queryUses(context, byProduct, 0, 5).total() > 0,
                "product filter should match enriched product labels");
    }

    @Test
    void likeWildcardsAreEscaped() {
        ReleaseContext context = catalog.resolve(null, null);
        CsvDataStore.UseQuery literal = new CsvDataStore.UseQuery(
                List.of(), null, "100%pure", null, null, null, null, null, null);
        int total = store.queryUses(context, literal, 0, 5).total();
        assertTrue(total == 0, "LIKE wildcard in user input must not broaden the match");
    }

    @Test
    void countriesCarryDerivedProjection() {
        ReleaseContext context = catalog.resolve(null, null);
        var countries = store.countries(context);
        assertFalse(countries.isEmpty(), "jurisdiction nodes should be projected to countries");
        assertTrue(countries.get(0).containsKey("jurisdiction_name"),
                "countries should carry jurisdiction_name");
        assertTrue(countries.get(0).containsKey("sovereign_country"));
        assertTrue(countries.get(0).containsKey("map_id"));
        String mapId = String.valueOf(countries.get(0).get("map_id"));
        assertTrue(mapId.matches("\\d+"), "map_id should be a numeric ISO code for the world map, got " + mapId);
        assertTrue(((Number) countries.get(0).get("nodes")).longValue() > 0,
                "derived countries should carry live node counts");
    }

    @Test
    void overviewCarriesComputedCoverage() {
        ReleaseContext context = catalog.resolve(null, null);
        var overview = store.overview(context);
        assertFalse(overview.coverage().isEmpty(), "coverage should be computed from kg edges in full mode");
        assertTrue(overview.coverage().get(0).containsKey("crop_english_given_source"));
        assertTrue(overview.coverage().get(0).containsKey("jurisdiction"));
    }

    @Test
    void releaseSummaryCarriesArtifacts() {
        var summary = catalog.summary(RELEASE);
        assertNotNull(summary.artifacts(), "release summary should list artifacts");
        assertFalse(summary.artifacts().isEmpty(), "release package should expose downloadable artifacts");
        Map<String, Object> first = summary.artifacts().get(0);
        assertTrue(first.containsKey("path"));
        assertTrue(first.containsKey("sha256"));
        assertTrue(first.containsKey("url"));
        assertTrue(String.valueOf(first.get("url")).startsWith("/api/v1/releases/"),
                "artifact url should point at the release-files endpoint");
    }

    private static PestKgProperties properties() {
        PestKgProperties value = new PestKgProperties();
        value.setDataDir(Path.of("../../../data/releases"));
        value.setStateDir(Path.of("../../../data/state"));
        value.setDefaultRelease(RELEASE);
        return value;
    }
}
