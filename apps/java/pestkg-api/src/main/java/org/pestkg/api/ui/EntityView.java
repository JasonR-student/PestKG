package org.pestkg.api.ui;

import com.vaadin.flow.component.html.H1;
import com.vaadin.flow.component.html.Paragraph;
import com.vaadin.flow.component.orderedlayout.VerticalLayout;
import com.vaadin.flow.router.BeforeEnterEvent;
import com.vaadin.flow.router.BeforeEnterObserver;
import com.vaadin.flow.router.PageTitle;
import com.vaadin.flow.router.Route;
import org.pestkg.api.CsvDataStore;
import org.pestkg.api.ReleaseCatalogService;
import org.pestkg.api.ReleaseContext;
import org.pestkg.domain.EntityData;

@Route(value = "entity/:entityId", layout = MainLayout.class)
@PageTitle("Entity | PestKG")
public class EntityView extends VerticalLayout implements BeforeEnterObserver {
    private final CsvDataStore store;
    private final ReleaseCatalogService catalog;
    private final H1 title = new H1();
    private final Paragraph details = new Paragraph();

    public EntityView(CsvDataStore store, ReleaseCatalogService catalog) {
        this.store = store;
        this.catalog = catalog;
        add(title, details);
    }

    @Override
    public void beforeEnter(BeforeEnterEvent event) {
        String id = event.getRouteParameters().get("entityId").orElse("");
        ReleaseContext context = catalog.resolve(null, null);
        EntityData entity = store.entity(context, id);
        if (entity == null) {
            title.setText("Entity not found");
            details.setText("No published sample row matches " + id + ".");
            return;
        }
        title.setText(entity.labelEn() == null || entity.labelEn().isBlank() ? entity.labelOriginal() : entity.labelEn());
        details.setText("ID: " + entity.id() + " · type: " + entity.type() + " · jurisdiction: " + entity.jurisdiction()
                + " · source: " + entity.sourceUrl());
    }
}
