package org.pestkg.api.ui;

import com.vaadin.flow.component.html.H1;
import com.vaadin.flow.component.html.H3;
import com.vaadin.flow.component.html.Paragraph;
import com.vaadin.flow.component.orderedlayout.VerticalLayout;
import com.vaadin.flow.router.PageTitle;
import com.vaadin.flow.router.Route;

@Route(value = "methods", layout = MainLayout.class)
@PageTitle("Methods | PestKG")
public class MethodsView extends VerticalLayout {
    public MethodsView() {
        add(new H1("Methods and provenance"));
        add(new H3("Version identity"));
        add(new Paragraph("Every page is pinned to one immutable release. Metrics expose the cutoff date, schema version, source scope, and distribution status."));
        add(new H3("Graph identity"));
        add(new Paragraph("Country-local entities remain distinct. Cross-jurisdiction traversal requires explicit exactMatch or lexicalAlignment assertions."));
        add(new H3("Temporal model"));
        add(new Paragraph("Canonical facts are append-only and support valid time plus transaction time. A release is a reproducible projection, not an in-place mutation."));
    }
}
