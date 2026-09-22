package org.pestkg.api;

import java.util.List;
import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.pestkg.domain.OverviewData;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/datasets")
public class DatasetController {
    private final ReleaseCatalogService catalog;
    private final ApiEnvelopeFactory envelopes;

    public DatasetController(ReleaseCatalogService catalog, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.envelopes = envelopes;
    }

    @GetMapping("/overview")
    public ApiEnvelope<OverviewData> overview(@RequestParam(required = false) String release,
                                               @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, catalog.overview(context));
    }

    @GetMapping("/coverage")
    public ApiEnvelope<List<Map<String, Object>>> coverage(@RequestParam(required = false) String release,
                                                            @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, catalog.readCountries(context));
    }

    @GetMapping("/schema")
    public ApiEnvelope<Map<String, Object>> schema(@RequestParam(required = false) String release,
                                                   @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        return envelopes.wrap(context, catalog.readSchema(context));
    }
}
