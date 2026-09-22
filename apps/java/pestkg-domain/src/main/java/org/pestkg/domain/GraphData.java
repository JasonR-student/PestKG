package org.pestkg.domain;

import java.util.List;

public record GraphData(List<EntityData> nodes, List<EdgeData> edges) {
}
