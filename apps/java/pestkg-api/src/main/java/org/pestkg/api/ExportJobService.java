package org.pestkg.api;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.pestkg.domain.RegistrationUseData;
import org.springframework.stereotype.Service;

@Service
public class ExportJobService {
    private final PestKgProperties properties;
    private final Map<String, ExportJob> jobs = new ConcurrentHashMap<>();

    public ExportJobService(PestKgProperties properties) { this.properties = properties; }

    public ExportJob create(ReleaseContext context, List<RegistrationUseData> rows) {
        String id = UUID.randomUUID().toString();
        Path directory = properties.getExportDir().toAbsolutePath().normalize();
        try {
            Files.createDirectories(directory);
            Path file = directory.resolve("registration-uses-" + id + ".csv");
            try (BufferedWriter writer = Files.newBufferedWriter(file, StandardCharsets.UTF_8)) {
                writer.write("use_id,jurisdiction,product_id,product_label_original,product_label_en,registration_status,registration_date,expiry_date,pairing_status,source_record_id,source_url");
                writer.newLine();
                for (RegistrationUseData row : rows) {
                    writer.write(String.join(",", csv(row.useId()), csv(row.jurisdiction()), csv(row.productId()),
                            csv(row.productLabelOriginal()), csv(row.productLabelEn()), csv(row.registrationStatus()),
                            csv(row.registrationDate()), csv(row.expiryDate()), csv(row.pairingStatus()),
                            csv(row.sourceRecordId()), csv(row.sourceUrl())));
                    writer.newLine();
                }
            }
            ExportJob job = new ExportJob(id, context.releaseId(), "completed", rows.size(), file);
            jobs.put(id, job);
            return job;
        } catch (IOException ex) {
            throw new ReleaseException("export_failed", "Unable to create export", 503, ex.getMessage());
        }
    }

    public ExportJob get(String id) {
        ExportJob job = jobs.get(id);
        if (job == null) throw new ReleaseException("job_not_found", "Export job not found", 404, Map.of("job_id", id));
        return job;
    }

    private static String csv(String value) {
        if (value == null) return "";
        String escaped = value.replace("\"", "\"\"");
        return escaped.contains(",") || escaped.contains("\"") || escaped.contains("\n") ? "\"" + escaped + "\"" : escaped;
    }

    public record ExportJob(String jobId, String releaseId, String status, int rows, Path file) { }
}
