/* menubar4 - a GTK4 application with a native three-menu menubar */
#include <gtk/gtk.h>
static void act(GSimpleAction *a, GVariant *p, gpointer d) { g_print("ACTIVATED %s\n", g_action_get_name(G_ACTION(a))); }
static void activate(GtkApplication *app, gpointer d)
{
	static const GActionEntry e[] = { {"new", act}, {"quit", act}, {"copy", act}, {"about", act} };
	g_action_map_add_action_entries(G_ACTION_MAP(app), e, 4, NULL);
	GMenu *bar = g_menu_new(), *file = g_menu_new(), *edit = g_menu_new(), *help = g_menu_new();
	g_menu_append(file, "New", "app.new"); g_menu_append(file, "Quit", "app.quit");
	g_menu_append(edit, "Copy", "app.copy"); g_menu_append(help, "About", "app.about");
	g_menu_append_submenu(bar, "File", G_MENU_MODEL(file));
	g_menu_append_submenu(bar, "Edit", G_MENU_MODEL(edit));
	g_menu_append_submenu(bar, "Help", G_MENU_MODEL(help));
	gtk_application_set_menubar(app, G_MENU_MODEL(bar));
	GtkWidget *w = gtk_application_window_new(app);
	gtk_window_set_title(GTK_WINDOW(w), "menubar4");
	gtk_window_set_default_size(GTK_WINDOW(w), 400, 200);
	gtk_window_present(GTK_WINDOW(w));
}
int main(int c, char **v) { GtkApplication *a = gtk_application_new("org.unitydistro.MenuBar4", 0); g_signal_connect(a, "activate", G_CALLBACK(activate), NULL); return g_application_run(G_APPLICATION(a), c, v); }
