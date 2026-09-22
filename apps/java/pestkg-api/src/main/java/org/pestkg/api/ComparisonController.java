package org.pestkg.api;

import java.util.List;
import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/comparisons")
public class ComparisonController {
    private final ReleaseCatalogService catalog;
    private final CsvDataStore store;
    private final ApiEnvelopeFactory envelopes;

    public ComparisonController(ReleaseCatalogService catalog, CsvDataStore store, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.envelopes = envelopes;
    }

    @GetMapping("/{question}")
    public ApiEnvelope<List<Map<String, String>>> comparison(@PathVariable String question,
                                                              @RequestParam(required = false) String q,
                                                              @RequestParam(defaultValue = "100") int limit,
                                                              @RequestParam(required = false) String release,
                                                              @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, store.comparison(context, question.toLowerCase(), q, limit));
    }
}
