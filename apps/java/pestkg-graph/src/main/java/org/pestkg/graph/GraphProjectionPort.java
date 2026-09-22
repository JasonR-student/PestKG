package org.pestkg.graph;

import org.pestkg.domain.GraphData;

public interface GraphProjectionPort {
    GraphData neighborhood(String releaseId, String nodeId, int depth, int nodeLimit, int edgeLimit);
    GraphData shortestPath(String releaseId, String startId, String endId, int maxDepth);
}
