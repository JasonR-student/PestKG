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
    private final DuckDbDataStore store;
    private final PestKgProperties properties;
    private final ApiEnvelopeFactory envelopes;

    public GraphController(ReleaseCatalogService catalog, DuckDbDataStore store, PestKgProperties properties, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.properties = properties;
        this.envelopes = envelopes;
    }

    @GetMapping("/neighborhood")
    public ApiEnvelope<GraphData> neighborhood(@RequestParam(required = false) String nodeId,
                                               @RequestParam(required = false) String node_id,
                                               @RequestParam(defaultValue = "1") int depth,
                                               @RequestParam(required = false) String release,
                                               @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        String id = nodeId != null ? nodeId : node_id;
        if (id == null || id.isBlank()) throw new IllegalArgumentException("nodeId is required");
        if (depth < 1 || depth > 2) throw new IllegalArgumentException("depth must be between 1 and 2");
        ReleaseContext context = catalog.resolve(release, header);
        GraphData data = store.neighborhood(context, id, depth, properties.getGraphNodeLimit(), properties.getGraphEdgeLimit());
        if (data.nodes().isEmpty()) throw new ReleaseException("graph_not_found", "Entity or neighborhood not found", 404, Map.of("node_id", id));
        return envelopes.wrap(context, data, store.mode(context));
    }

    @GetMapping("/path")
    public ApiEnvelope<GraphData> path(@RequestParam(required = false) String startId,
                                       @RequestParam(required = false) String start_id,
                                       @RequestParam(required = false) String endId,
                                       @RequestParam(required = false) String end_id,
                                       @RequestParam(defaultValue = "3") int maxDepth,
                                       @RequestParam(required = false) String release,
                                       @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        String start = startId != null ? startId : start_id;
        String end = endId != null ? endId : end_id;
        if (start == null || start.isBlank() || end == null || end.isBlank()) {
            throw new IllegalArgumentException("startId and endId are required");
        }
        if (maxDepth < 1 || maxDepth > 3) throw new IllegalArgumentException("maxDepth must be between 1 and 3");
        ReleaseContext context = catalog.resolve(release, header);
        GraphData data = store.shortestPath(context, start, end, maxDepth);
        return envelopes.wrap(context, data, store.mode(context));
    }
}
