package org.pestkg.api.ui;

import com.vaadin.flow.component.grid.Grid;
import com.vaadin.flow.component.html.H1;
import com.vaadin.flow.component.orderedlayout.VerticalLayout;
import com.vaadin.flow.router.PageTitle;
import com.vaadin.flow.router.Route;
import org.pestkg.api.ReleaseCatalogService;
import org.pestkg.domain.ReleaseSummary;

@Route(value = "releases", layout = MainLayout.class)
@PageTitle("Releases | PestKG")
public class ReleaseCatalogView extends VerticalLayout {
    public ReleaseCatalogView(ReleaseCatalogService catalog) {
        add(new H1("Release catalog"));
        Grid<ReleaseSummary> grid = new Grid<>(ReleaseSummary.class, false);
        grid.addColumn(ReleaseSummary::releaseId).setHeader("Release");
        grid.addColumn(ReleaseSummary::publishedAt).setHeader("Published");
        grid.addColumn(ReleaseSummary::cutoff).setHeader("Cutoff");
        grid.addColumn(ReleaseSummary::distributionStatus).setHeader("Distribution");
        grid.addColumn(item -> item.active() ? "active" : "").setHeader("State");
        grid.setItems(catalog.list());
        grid.setHeight("520px");
        add(grid);
    }
}
