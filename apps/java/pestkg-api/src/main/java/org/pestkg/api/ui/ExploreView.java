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
import org.pestkg.domain.EntityData;

@Route(value = "explore", layout = MainLayout.class)
@PageTitle("Explore | PestKG")
public class ExploreView extends VerticalLayout {
    private final CsvDataStore store;
    private final ReleaseContext context;
    private final Grid<EntityData> grid = new Grid<>(EntityData.class, false);
    private final TextField search = new TextField("Entity search");

    public ExploreView(ReleaseCatalogService catalog, CsvDataStore store) {
        this.store = store;
        this.context = catalog.resolve(null, null);
        add(new H1("Explore entities"));
        search.setPlaceholder("Search by source label, English label, or ID");
        Button run = new Button("Search", event -> refresh());
        add(new HorizontalLayout(search, run));
        grid.addColumn(EntityData::id).setHeader("ID").setAutoWidth(true);
        grid.addColumn(EntityData::type).setHeader("Type").setAutoWidth(true);
        grid.addColumn(EntityData::labelOriginal).setHeader("Original label");
        grid.addColumn(EntityData::labelEn).setHeader("English label");
        grid.addColumn(EntityData::jurisdiction).setHeader("Jurisdiction");
        grid.setHeight("560px");
        add(grid);
        refresh();
    }

    private void refresh() {
        grid.setItems(store.search(context, search.getValue(), null, null, 100));
    }
}
