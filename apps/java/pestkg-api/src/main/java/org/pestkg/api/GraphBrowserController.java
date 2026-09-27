package org.pestkg.api;

import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/graph")
public class GraphBrowserController {
    private final ReleaseCatalogService catalog;
    private final GraphBrowserStore store;
    private final ApiEnvelopeFactory envelopes;

    public GraphBrowserController(ReleaseCatalogService catalog, GraphBrowserStore store, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.envelopes = envelopes;
    }

    @GetMapping("/catalog")
    public ApiEnvelope<Map<String, Object>> catalog(@RequestParam(required = false) String release,
        @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.catalog(context), "full");
    }

    @PostMapping("/query")
    public ApiEnvelope<GraphBrowserStore.Result> query(@RequestBody GraphBrowserStore.Query query,
        @RequestParam(required = false) String release,
        @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.query(context, query, null), "full");
    }

    @PostMapping("/expand")
    public ApiEnvelope<GraphBrowserStore.Result> expand(@RequestBody GraphBrowserStore.Query query,
        @RequestParam String node_id, @RequestParam(required = false) String release,
        @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.query(context, query, node_id), "full");
    }
}
