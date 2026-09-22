package org.pestkg.api.ui;

import com.vaadin.flow.component.html.H1;
import com.vaadin.flow.component.html.H3;
import com.vaadin.flow.component.html.Paragraph;
import com.vaadin.flow.component.orderedlayout.HorizontalLayout;
import com.vaadin.flow.component.orderedlayout.VerticalLayout;
import com.vaadin.flow.router.PageTitle;
import com.vaadin.flow.router.Route;
import org.pestkg.api.ReleaseCatalogService;
import org.pestkg.api.ReleaseContext;
import org.pestkg.domain.OverviewData;

@Route(value = "", layout = MainLayout.class)
@PageTitle("Overview | PestKG")
public class OverviewView extends VerticalLayout {
    public OverviewView(ReleaseCatalogService catalog) {
        ReleaseContext context = catalog.resolve(null, null);
        OverviewData overview = catalog.overview(context);
        add(new H1("Multicountry pesticide knowledge graph"));
        add(new Paragraph("Release " + context.releaseId() + " · cutoff " + overview.cutoff()
                + " · distribution " + overview.distributionStatus()));

        HorizontalLayout metrics = new HorizontalLayout();
        overview.inventory().forEach((key, value) -> metrics.add(metric(key, value)));
        add(metrics);
        add(new H3("Coverage and limitations"));
        add(new Paragraph("This view is release-pinned and every value is traceable to the selected immutable data package."));
        overview.knownLimitations().forEach(item -> add(new Paragraph("• " + item)));
    }

    private VerticalLayout metric(String label, Object value) {
        VerticalLayout box = new VerticalLayout(new H3(label), new Paragraph(String.valueOf(value)));
        box.getStyle().set("border-bottom", "1px solid var(--lumo-contrast-10pct)");
        return box;
    }
}
