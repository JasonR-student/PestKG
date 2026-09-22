package org.pestkg.api.ui;

import com.vaadin.flow.component.applayout.AppLayout;
import com.vaadin.flow.component.applayout.DrawerToggle;
import com.vaadin.flow.component.html.H2;
import com.vaadin.flow.component.html.Span;
import com.vaadin.flow.component.orderedlayout.VerticalLayout;
import com.vaadin.flow.router.RouterLink;

public class MainLayout extends AppLayout {
    public MainLayout() {
        DrawerToggle toggle = new DrawerToggle();
        H2 title = new H2("PestKG research portal");
        title.getStyle().set("font-size", "var(--lumo-font-size-l)").set("margin", "0");
        addToNavbar(toggle, title);

        VerticalLayout navigation = new VerticalLayout(
                new Span("Workspace"),
                new RouterLink("Overview", OverviewView.class),
                new RouterLink("Explore", ExploreView.class),
                new RouterLink("Graph", GraphView.class),
                new RouterLink("Releases", ReleaseCatalogView.class),
                new RouterLink("Methods", MethodsView.class));
        navigation.setPadding(true);
        addToDrawer(navigation);
    }
}
