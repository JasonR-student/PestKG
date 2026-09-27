package org.pestkg.api;

import static org.junit.jupiter.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class GraphBrowserTest {
    private static final PestKgProperties PROPERTIES = properties();
    private static final ReleaseCatalogService CATALOG = new ReleaseCatalogService(PROPERTIES, new ObjectMapper());
    private static final GraphBrowserStore STORE = new GraphBrowserStore(CATALOG, PROPERTIES, new ObjectMapper());
    private static final ReleaseContext CONTEXT = CATALOG.resolve(null, null);

    private static PestKgProperties properties() {
        PestKgProperties properties = new PestKgProperties();
        properties.setDataDir(Path.of("../../../data/releases").toAbsolutePath().normalize());
        properties.setReferenceDir(Path.of("../../../data/reference-graphs").toAbsolutePath().normalize());
        properties.setDefaultRelease("PestKG_A_Data_Release_v1.0");
        return properties;
    }

    @SuppressWarnings("unchecked")
    @Test void catalogPreservesJurisdictionsAndIndependentWebsites() {
        List<Map<String, Object>> scopes = (List<Map<String, Object>>) STORE.catalog(CONTEXT).get("scopes");
        assertEquals(12, scopes.stream().filter(scope -> scope.get("kind").equals("jurisdiction")).count());
        assertEquals(12, scopes.stream().filter(scope -> scope.get("kind").equals("source")).count());
        assertEquals(7, scopes.stream().filter(scope -> scope.get("kind").equals("reference")).count());
        assertTrue(scopes.stream().anyMatch(scope -> scope.get("id").equals("jurisdiction:TW")));
        assertEquals(0, STORE.catalog(CONTEXT).get("exact_identity_links"));
    }

    @Test void apvmaScopeContainsBusinessRecordsAndExplicitPropertyProjection() {
        var result = STORE.query(CONTEXT, new GraphBrowserStore.Query("source:apvma_pubcris", "", "Frutor Fungicide", 120, true), null);
        assertTrue(result.nodes().stream().anyMatch(node -> node.type().equals("PesticideProduct")));
        assertTrue(result.nodes().size() > 2);
        assertTrue(result.edges().stream().anyMatch(edge -> edge.predicate().equals("FROM_SNAPSHOT") && Boolean.FALSE.equals(edge.properties().get("stored_fact"))));
        assertEndpoints(result);
        var expanded = STORE.query(CONTEXT, new GraphBrowserStore.Query("source:apvma_pubcris", "", "", 120, true),
            "SRC_36b5fb76cbd14a4f95f68131824e2571");
        assertTrue(expanded.nodes().size() > 2);
        assertEndpoints(expanded);
    }

    @Test void provenanceCanBeExcludedWithoutLosingBusinessGraph() {
        var result = STORE.query(CONTEXT, new GraphBrowserStore.Query("jurisdiction:AU", "", "Frutor Fungicide", 60, false), null);
        assertFalse(result.nodes().isEmpty());
        assertTrue(result.edges().stream().noneMatch(edge -> edge.predicate().equals("FROM_SNAPSHOT")));
        assertEndpoints(result);
    }

    @Test void taiwanScopeAndReferenceScopesDoNotMergeRegulatoryIdentity() {
        var taiwan = STORE.query(CONTEXT, new GraphBrowserStore.Query("jurisdiction:TW", "", "", 60, false), null);
        assertFalse(taiwan.nodes().isEmpty());
        assertTrue(taiwan.nodes().stream().allMatch(node -> node.jurisdiction().equals("TW")));
        for (var entry : Map.of("reference:CHEBI", "glyphosate", "reference:AGROVOC", "cucumbers").entrySet()) {
            var result = STORE.query(CONTEXT, new GraphBrowserStore.Query(entry.getKey(), "", entry.getValue(), 60, true), null);
            assertFalse(result.nodes().isEmpty(), entry.getKey());
            assertTrue(result.nodes().stream().allMatch(node -> node.id().startsWith("REF_")));
            assertTrue(result.edges().stream().noneMatch(edge -> edge.predicate().equals("EXACT_CHEMICAL_IDENTITY")));
            assertEndpoints(result);
        }
    }

    @Test void invalidScopeLimitsAndSqlLikeTextAreHandled() {
        assertThrows(IllegalArgumentException.class, () -> STORE.query(CONTEXT, new GraphBrowserStore.Query("reference:missing", "", "", 120, false), null));
        assertThrows(IllegalArgumentException.class, () -> STORE.query(CONTEXT, new GraphBrowserStore.Query("all", "", "", 301, false), null));
        var empty = STORE.query(CONTEXT, new GraphBrowserStore.Query("jurisdiction:AU", "", "' OR 1=1 --", 60, false), null);
        assertTrue(empty.nodes().isEmpty());
    }

    private static void assertEndpoints(GraphBrowserStore.Result graph) {
        var ids = graph.nodes().stream().map(node -> node.id()).collect(java.util.stream.Collectors.toSet());
        assertTrue(graph.edges().stream().allMatch(edge -> ids.contains(edge.startId()) && ids.contains(edge.endId())));
        assertTrue(graph.nodes().size() <= graph.nodeLimit());
        assertTrue(graph.edges().size() <= PROPERTIES.getGraphEdgeLimit());
    }
}
