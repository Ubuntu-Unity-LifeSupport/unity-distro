/*
 * unity-gtk4-shim - experiment for Layer B of unity-distro.
 *
 * GTK4 has no module loading mechanism, so the way appmenu-gtk-module reaches
 * GTK3 applications is unavailable. What is available is symbol interposition,
 * the same technique libgtk-nocsd already uses in the Unity session.
 *
 * GTK4 still exports a menubar over org.gtk.Menus and advertises it through
 * _GTK_MENUBAR_OBJECT_PATH, and the Unity panel renders it. Applications
 * simply never call gtk_application_set_menubar(): their menu lives in a
 * GtkMenuButton in the header bar.
 *
 * The menubar has to be set before the window is realized - attaching one
 * afterwards silently does nothing. gtk_window_present() is the last moment
 * the application controls before realize, so that is where we intervene.
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <unistd.h>
#include <gtk/gtk.h>

static int verbose(void) {
	static int v = -1;
	if (v < 0)
		v = getenv("UNITY_GTK4_SHIM_DEBUG") != NULL;
	return v;
}

/*
 * Log to a file rather than stderr when UNITY_GTK4_SHIM_LOG is set. The window
 * is often created in a different process from the one launched - file-roller
 * and simple-scan both do this - and that process inherits the environment but
 * not the caller's redirected stderr, so stderr output simply disappears.
 */
static void note_out(const char *fmt, ...)
{
	if (!verbose())
		return;

	va_list ap;
	const char *path = getenv("UNITY_GTK4_SHIM_LOG");
	FILE *out = stderr;

	if (path != NULL) {
		FILE *f = fopen(path, "a");
		if (f != NULL)
			out = f;
	}

	fprintf(out, "[unity-gtk4-shim %d] ", (int)getpid());
	va_start(ap, fmt);
	vfprintf(out, fmt, ap);
	va_end(ap);
	fputc('\n', out);
	fflush(out);

	if (out != stderr)
		fclose(out);
}

#define note(...) note_out(__VA_ARGS__)

/* Depth-first search for the first GtkMenuButton carrying a menu model. */
static GMenuModel *find_menu_model(GtkWidget *widget, int depth)
{
	if (widget == NULL || depth > 32)
		return NULL;

	if (GTK_IS_MENU_BUTTON(widget)) {
		GMenuModel *model =
			gtk_menu_button_get_menu_model(GTK_MENU_BUTTON(widget));
		if (model != NULL) {
			note("found GtkMenuButton with a model at depth %d", depth);
			return model;
		}
	}

	if (GTK_IS_POPOVER_MENU_BAR(widget)) {
		GMenuModel *model = gtk_popover_menu_bar_get_menu_model(
			GTK_POPOVER_MENU_BAR(widget));
		if (model != NULL) {
			note("found GtkPopoverMenuBar with a model at depth %d", depth);
			return model;
		}
	}

	for (GtkWidget *child = gtk_widget_get_first_child(widget);
	     child != NULL; child = gtk_widget_get_next_sibling(child)) {
		GMenuModel *model = find_menu_model(child, depth + 1);
		if (model != NULL)
			return model;
	}

	return NULL;
}

/* Print the top level of a model: what a hamburger menu is actually made of. */
static void dump_model(GMenuModel *model)
{
	if (!verbose() || model == NULL)
		return;

	int n = g_menu_model_get_n_items(model);
	note("model has %d top-level item(s)", n);

	for (int i = 0; i < n; i++) {
		char *label = NULL;
		gboolean has_label = g_menu_model_get_item_attribute(
			model, i, G_MENU_ATTRIBUTE_LABEL, "s", &label);
		GMenuModel *section =
			g_menu_model_get_item_link(model, i, G_MENU_LINK_SECTION);
		GMenuModel *submenu =
			g_menu_model_get_item_link(model, i, G_MENU_LINK_SUBMENU);

		note("  [%d] %s%s%s  label=%s", i,
		     section ? "section" : "", submenu ? "submenu" : "",
		     (!section && !submenu) ? "item" : "",
		     has_label ? label : "(none)");

		if (section != NULL) {
			note("       section holds %d item(s)",
			     g_menu_model_get_n_items(section));
			g_object_unref(section);
		}
		if (submenu != NULL)
			g_object_unref(submenu);
		if (has_label)
			g_free(label);
	}
}

static void attach_menubar(GtkWindow *window)
{
	GtkApplication *app = gtk_window_get_application(window);

	if (app == NULL) {
		note("window has no GtkApplication, nothing to attach to");
		return;
	}
	if (gtk_application_get_menubar(app) != NULL) {
		note("application already has a menubar, leaving it alone");
		return;
	}

	/* The title bar is not part of the ordinary child tree. */
	GMenuModel *model = find_menu_model(gtk_window_get_titlebar(window), 0);
	if (model == NULL)
		model = find_menu_model(gtk_window_get_child(window), 0);

	if (model == NULL) {
		note("no menu model found in this window");
		return;
	}

	dump_model(model);

	const char *app_label = g_get_application_name();
	if (app_label == NULL)
		app_label = "Menu";

	if (getenv("UNITY_GTK4_SHIM_DIRECT") != NULL) {
		/* Hand the model over as the menubar with no wrapper at all. */
		gtk_application_set_menubar(app, model);
		note("menubar attached directly, no wrapper");
		return;
	}

	GMenu *menubar = g_menu_new();

	if (getenv("UNITY_GTK4_SHIM_FLATTEN") != NULL) {
		/*
		 * Promote each section of the hamburger menu to its own
		 * top-level menu, which is the shape Unity expects from a
		 * GTK3 application. Sections mostly carry no label, so this
		 * only works as far as the labels do.
		 */
		int n = g_menu_model_get_n_items(model);
		int promoted = 0;

		for (int i = 0; i < n; i++) {
			GMenuModel *section = g_menu_model_get_item_link(
				model, i, G_MENU_LINK_SECTION);
			if (section == NULL)
				continue;

			char *label = NULL;
			if (!g_menu_model_get_item_attribute(
				    model, i, G_MENU_ATTRIBUTE_LABEL, "s",
				    &label))
				label = NULL;

			g_menu_append_submenu(menubar,
					      label ? label : app_label,
					      section);
			promoted++;

			g_free(label);
			g_object_unref(section);
		}

		note("flattened: promoted %d section(s) of %d", promoted, n);

		if (promoted == 0) {
			g_menu_append_submenu(menubar, app_label, model);
			note("nothing to promote, fell back to a single menu");
		}
	} else {
		/* One top-level entry holding the whole hamburger menu. */
		g_menu_append_submenu(menubar, app_label, model);
		note("menubar attached, labelled \"%s\"", app_label);
	}

	gtk_application_set_menubar(app, G_MENU_MODEL(menubar));
	g_object_unref(menubar);
}

/*
 * Interposing gtk_window_present / gtk_widget_set_visible / gtk_widget_show
 * catches applications that show their window themselves, but not ones where
 * the call is made from inside GTK or libadwaita - file-roller is one, and
 * none of the three ever fired for it.
 *
 * So do what appmenu-gtk-module does for GTK3: overwrite realize in the class
 * vtable. The reason that module cannot do it under GTK4 is that it has no way
 * to get loaded, which is exactly what LD_PRELOAD solves. Type registration
 * does not need gtk_init(), so g_type_class_ref works from a constructor.
 */

static void (*real_window_realize)(GtkWidget *) = NULL;
static void (*real_app_window_realize)(GtkWidget *) = NULL;

static void shim_window_realize(GtkWidget *widget)
{
	note("realize (GtkWindow)");
	attach_menubar(GTK_WINDOW(widget));
	if (real_window_realize != NULL)
		real_window_realize(widget);
}

static void shim_app_window_realize(GtkWidget *widget)
{
	note("realize (GtkApplicationWindow)");
	attach_menubar(GTK_WINDOW(widget));
	if (real_app_window_realize != NULL)
		real_app_window_realize(widget);
}

__attribute__((constructor)) static void shim_init(void)
{
	note("env: DIRECT=%s FLATTEN=%s LOG=%s",
	     getenv("UNITY_GTK4_SHIM_DIRECT") ? "set" : "-",
	     getenv("UNITY_GTK4_SHIM_FLATTEN") ? "set" : "-",
	     getenv("UNITY_GTK4_SHIM_LOG") ? getenv("UNITY_GTK4_SHIM_LOG") : "-");

	GtkWidgetClass *window_class = g_type_class_ref(GTK_TYPE_WINDOW);
	if (window_class != NULL) {
		real_window_realize = window_class->realize;
		window_class->realize = shim_window_realize;
		note("hooked GtkWindow::realize");
	}

	GtkWidgetClass *app_window_class =
		g_type_class_ref(GTK_TYPE_APPLICATION_WINDOW);
	if (app_window_class != NULL &&
	    app_window_class->realize != real_window_realize) {
		real_app_window_realize = app_window_class->realize;
		app_window_class->realize = shim_app_window_realize;
		note("hooked GtkApplicationWindow::realize");
	}
}
