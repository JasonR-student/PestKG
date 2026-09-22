package org.pestkg.api;

import java.nio.file.Path;
import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "pestkg")
public class PestKgProperties {
    private Path dataDir = Path.of("data/releases");
    private Path stateDir = Path.of("data/state");
    private Path exportDir = Path.of("runtime/java-exports");
    private String defaultRelease = "2026.08.3_federated";
    private int graphNodeLimit = 1_000;
    private int graphEdgeLimit = 2_000;

    public Path getDataDir() { return dataDir; }
    public void setDataDir(Path dataDir) { this.dataDir = dataDir; }
    public Path getStateDir() { return stateDir; }
    public void setStateDir(Path stateDir) { this.stateDir = stateDir; }
    public Path getExportDir() { return exportDir; }
    public void setExportDir(Path exportDir) { this.exportDir = exportDir; }
    public String getDefaultRelease() { return defaultRelease; }
    public void setDefaultRelease(String defaultRelease) { this.defaultRelease = defaultRelease; }
    public int getGraphNodeLimit() { return graphNodeLimit; }
    public void setGraphNodeLimit(int graphNodeLimit) { this.graphNodeLimit = graphNodeLimit; }
    public int getGraphEdgeLimit() { return graphEdgeLimit; }
    public void setGraphEdgeLimit(int graphEdgeLimit) { this.graphEdgeLimit = graphEdgeLimit; }
}
