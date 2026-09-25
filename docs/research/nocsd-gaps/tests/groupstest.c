/* groupstest - header bar menu whose items use a group inserted on the
   window later ("grp."), replaced, and removed, like deja-dup and sudoku.
   Stdin commands: i = insert a new group, r = remove it, d = disable grp.hello,
   t = print the toggle's state. Every activation prints one line. */
#include <gtk/gtk.h>
static GtkWidget *win;
static int generation;
static void hello(GSimpleAction *a, GVariant *p, gpointer d) { g_print("ACTIVATED grp.hello gen %d\n", GPOINTER_TO_INT(d)); }
static void toggle(GSimpleAction *a, GVariant *p, gpointer d)
{
	GVariant *s = g_action_get_state(G_ACTION(a));
	g_simple_action_set_state(a, g_variant_new_boolean(!g_variant_get_boolean(s)));
	g_print("ACTIVATED grp.toggle -> %d\n", !g_variant_get_boolean(s));
	g_variant_unref(s);
}
static GSimpleActionGroup *group;
static gboolean command(GIOChannel *c, GIOCondition cond, gpointer d)
{
	gchar *line = NULL;
	if (g_io_channel_read_line(c, &line, NULL, NULL, NULL) != G_IO_STATUS_NORMAL) return FALSE;
	if (line[0] == 'i') {
		group = g_simple_action_group_new();
		GSimpleAction *h = g_simple_action_new("hello", NULL);
		g_signal_connect(h, "activate", G_CALLBACK(hello), GINT_TO_POINTER(++generation));
		GSimpleAction *t = g_simple_action_new_stateful("toggle", NULL, g_variant_new_boolean(FALSE));
		g_signal_connect(t, "activate", G_CALLBACK(toggle), NULL);
		g_action_map_add_action(G_ACTION_MAP(group), G_ACTION(h));
		g_action_map_add_action(G_ACTION_MAP(group), G_ACTION(t));
		gtk_widget_insert_action_group(win, "grp", G_ACTION_GROUP(group));
		g_print("INSERTED gen %d\n", generation);
	} else if (line[0] == 'r') {
		gtk_widget_insert_action_group(win, "grp", NULL);
		g_print("REMOVED\n");
	} else if (line[0] == 'd' && group) {
		g_simple_action_set_enabled(G_SIMPLE_ACTION(g_action_map_lookup_action(G_ACTION_MAP(group), "hello")), FALSE);
		g_print("DISABLED hello\n");
	}
	g_free(line);
	return TRUE;
}
static void activate(GtkApplication *app, gpointer d)
{
	GMenu *m = g_menu_new(); GMenuItem *i;
	g_menu_append(m, "Hello", "grp.hello");
	g_menu_append(m, "Toggle", "grp.toggle");
	i = g_menu_item_new("Hidden when missing", "grp.hello");
	g_menu_item_set_attribute(i, "hidden-when", "s", "action-missing");
	g_menu_append_item(m, i);
	win = gtk_application_window_new(app);
	GtkWidget *hb = gtk_header_bar_new(), *mb = gtk_menu_button_new();
	gtk_menu_button_set_menu_model(GTK_MENU_BUTTON(mb), G_MENU_MODEL(m));
	gtk_menu_button_set_primary(GTK_MENU_BUTTON(mb), TRUE);
	gtk_header_bar_pack_end(GTK_HEADER_BAR(hb), mb);
	gtk_window_set_titlebar(GTK_WINDOW(win), hb);
	gtk_window_set_title(GTK_WINDOW(win), "groupstest");
	gtk_window_set_default_size(GTK_WINDOW(win), 400, 200);
	gtk_window_present(GTK_WINDOW(win));
	GIOChannel *c = g_io_channel_unix_new(0);
	g_io_add_watch(c, G_IO_IN, command, NULL);
}
int main(int c, char **v) { GtkApplication *a = gtk_application_new("org.unitydistro.GroupsTest", 0); g_signal_connect(a, "activate", G_CALLBACK(activate), NULL); return g_application_run(G_APPLICATION(a), c, v); }
