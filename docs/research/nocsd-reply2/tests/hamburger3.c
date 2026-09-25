/* hamburger3 - a GTK3 application whose only menu is a header bar menu button */
#include <gtk/gtk.h>
static void act(GSimpleAction *a, GVariant *p, gpointer d) { g_print("ACTIVATED %s\n", g_action_get_name(G_ACTION(a))); }
static void activate(GtkApplication *app, gpointer d)
{
	static const GActionEntry e[] = { {"new-window", act}, {"preferences", act}, {"about", act} };
	g_action_map_add_action_entries(G_ACTION_MAP(app), e, 3, NULL);
	GMenu *m = g_menu_new(), *s1 = g_menu_new(), *s2 = g_menu_new();
	g_menu_append(s1, "New Window", "app.new-window"); g_menu_append(s2, "Preferences", "app.preferences"); g_menu_append(s2, "About", "app.about");
	g_menu_append_section(m, NULL, G_MENU_MODEL(s1)); g_menu_append_section(m, NULL, G_MENU_MODEL(s2));
	GtkWidget *w = gtk_application_window_new(app), *hb = gtk_header_bar_new(), *mb = gtk_menu_button_new();
	gtk_menu_button_set_menu_model(GTK_MENU_BUTTON(mb), G_MENU_MODEL(m));
	gtk_header_bar_pack_end(GTK_HEADER_BAR(hb), mb); gtk_header_bar_set_show_close_button(GTK_HEADER_BAR(hb), TRUE);
	gtk_header_bar_set_title(GTK_HEADER_BAR(hb), "hamburger3"); gtk_window_set_titlebar(GTK_WINDOW(w), hb);
	gtk_window_set_default_size(GTK_WINDOW(w), 400, 200); gtk_widget_show_all(w);
}
int main(int c, char **v) { GtkApplication *a = gtk_application_new("org.unitydistro.Hamburger3", 0); g_signal_connect(a, "activate", G_CALLBACK(activate), NULL); return g_application_run(G_APPLICATION(a), c, v); }
