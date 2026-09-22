package org.pestkg.api;

import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.pestkg.domain.GraphData;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/graph")
public class GraphController {
    private final ReleaseCatalogService catalog;
    private final CsvDataStore store;
    private final PestKgProperties properties;
    private final ApiEnvelopeFactory envelopes;

    public GraphController(ReleaseCatalogService catalog, CsvDataStore store, PestKgProperties properties, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.properties = properties;
        this.envelopes = envelopes;
    }

    @GetMapping("/neighborhood")
    public ApiEnvelope<GraphData> neighborhood(@RequestParam String nodeId,
                                                @RequestParam(defaultValue = "1") int depth,
                                                @RequestParam(required = false) String release,
                                                @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        if (depth < 1 || depth > 2) throw new IllegalArgumentException("depth must be between 1 and 2");
        ReleaseContext context = catalog.resolve(release, header);
        GraphData data = store.neighborhood(context, nodeId, depth, properties.getGraphNodeLimit(), properties.getGraphEdgeLimit());
        if (data.nodes().isEmpty()) throw new ReleaseException("graph_not_found", "Entity or neighborhood not found", 404, Map.of("node_id", nodeId));
        return envelopes.wrap(context, data);
    }

    @GetMapping("/path")
    public ApiEnvelope<GraphData> path(@RequestParam String startId,
                                       @RequestParam String endId,
                                       @RequestParam(defaultValue = "3") int maxDepth,
                                       @RequestParam(required = false) String release,
                                       @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        if (maxDepth < 1 || maxDepth > 3) throw new IllegalArgumentException("maxDepth must be between 1 and 3");
        ReleaseContext context = catalog.resolve(release, header);
        GraphData data = store.shortestPath(context, startId, endId, maxDepth);
        return envelopes.wrap(context, data);
    }
}
