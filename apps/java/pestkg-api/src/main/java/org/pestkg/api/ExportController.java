package org.pestkg.api;

import java.util.Map;
import org.pestkg.domain.ApiEnvelope;
import org.springframework.core.io.Resource;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1")
public class ExportController {
    private final ReleaseCatalogService catalog;
    private final CsvDataStore store;
    private final ExportJobService jobs;
    private final ApiEnvelopeFactory envelopes;

    public ExportController(ReleaseCatalogService catalog, CsvDataStore store, ExportJobService jobs, ApiEnvelopeFactory envelopes) {
        this.catalog = catalog;
        this.store = store;
        this.jobs = jobs;
        this.envelopes = envelopes;
    }

    @PostMapping("/exports")
    public ApiEnvelope<Map<String, Object>> export(@RequestBody(required = false) RegistrationUseController.RegistrationUseQueryRequest request,
                                                    @RequestParam(required = false) String release,
                                                    @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ReleaseContext context = catalog.resolve(release, header);
        RegistrationUseController.RegistrationUseQueryRequest safe = request == null
                ? new RegistrationUseController.RegistrationUseQueryRequest(null, null, 200)
                : request;
        var job = jobs.create(context, store.queryUses(context, safe.toUseQuery()));
        return envelopes.wrap(context, Map.of("job_id", job.jobId(), "status", job.status(), "rows", job.rows(),
                "download_url", "/api/v1/artifacts/" + job.jobId() + "/download"));
    }

    @GetMapping("/jobs/{jobId}")
    public ApiEnvelope<Map<String, Object>> job(@PathVariable String jobId,
                                                @RequestParam(required = false) String release,
                                                @RequestHeader(name = "X-PestKG-Release", required = false) String header) {
        ExportJobService.ExportJob job = jobs.get(jobId);
        ReleaseContext context = catalog.resolve(release == null ? job.releaseId() : release, header);
        return envelopes.wrap(context, Map.of("job_id", job.jobId(), "status", job.status(), "rows", job.rows(), "release_id", job.releaseId()));
    }

    @GetMapping("/artifacts/{jobId}/download")
    public ResponseEntity<Resource> download(@PathVariable String jobId) {
        ExportJobService.ExportJob job = jobs.get(jobId);
        Resource resource = new FileSystemResource(job.file());
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("text/csv; charset=UTF-8"))
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"registration-uses-" + job.jobId() + ".csv\"")
                .body(resource);
    }
}
