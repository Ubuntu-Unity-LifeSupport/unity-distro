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
#include <gtk/gtk.h>

static int verbose(void) {
	static int v = -1;
	if (v < 0)
		v = getenv("UNITY_GTK4_SHIM_DEBUG") != NULL;
	return v;
}

#define note(...)                                                              \
	do {                                                                   \
		if (verbose()) {                                               \
			fprintf(stderr, "[unity-gtk4-shim] ");                 \
			fprintf(stderr, __VA_ARGS__);                          \
			fputc('\n', stderr);                                   \
		}                                                              \
	} while (0)

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

	/*
	 * A menubar model is a list of submenus. What we found is usually a
	 * flat list of sections, so wrap it in one submenu rather than hand it
	 * over directly and hope it renders.
	 */
	const char *label = g_get_application_name();
	if (label == NULL)
		label = "Menu";

	GMenu *menubar = g_menu_new();
	g_menu_append_submenu(menubar, label, model);
	gtk_application_set_menubar(app, G_MENU_MODEL(menubar));
	g_object_unref(menubar);

	note("menubar attached, labelled \"%s\"", label);
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
