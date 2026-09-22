package org.pestkg.api.ui;

import com.vaadin.flow.component.button.Button;
import com.vaadin.flow.component.grid.Grid;
import com.vaadin.flow.component.html.H1;
import com.vaadin.flow.component.orderedlayout.HorizontalLayout;
import com.vaadin.flow.component.orderedlayout.VerticalLayout;
import com.vaadin.flow.component.textfield.TextField;
import com.vaadin.flow.router.PageTitle;
import com.vaadin.flow.router.Route;
import org.pestkg.api.CsvDataStore;
import org.pestkg.api.ReleaseCatalogService;
import org.pestkg.api.ReleaseContext;
import org.pestkg.domain.EdgeData;
import org.pestkg.domain.GraphData;

@Route(value = "graph", layout = MainLayout.class)
@PageTitle("Graph | PestKG")
public class GraphView extends VerticalLayout {
    private final CsvDataStore store;
    private final ReleaseContext context;
    private final TextField nodeId = new TextField("Root node ID");
    private final Grid<EdgeData> edges = new Grid<>(EdgeData.class, false);

    public GraphView(ReleaseCatalogService catalog, CsvDataStore store) {
        this.context = catalog.resolve(null, null);
        this.store = store;
        add(new H1("Bounded graph inspection"));
        Button load = new Button("Load neighborhood", event -> refresh());
        add(new HorizontalLayout(nodeId, load));
        edges.addColumn(EdgeData::id).setHeader("Edge");
        edges.addColumn(EdgeData::predicate).setHeader("Predicate");
        edges.addColumn(EdgeData::startId).setHeader("Start");
        edges.addColumn(EdgeData::endId).setHeader("End");
        edges.setHeight("480px");
        add(edges);
    }

    private void refresh() {
        GraphData graph = store.neighborhood(context, nodeId.getValue(), 1, 1000, 2000);
        edges.setItems(graph.edges());
    }
}
