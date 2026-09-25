/* menubar3 - a GTK3 window with a classic GtkMenuBar (appmenu-gtk-module exports it) */
#include <gtk/gtk.h>
static void on(GtkMenuItem *i, gpointer d) { g_print("ACTIVATED %s\n", gtk_menu_item_get_label(i)); }
static GtkWidget *menu(GtkWidget *bar, const char *name, const char **items)
{
	GtkWidget *top = gtk_menu_item_new_with_label(name), *m = gtk_menu_new();
	for (; *items; items++) { GtkWidget *it = gtk_menu_item_new_with_label(*items); g_signal_connect(it, "activate", G_CALLBACK(on), NULL); gtk_menu_shell_append(GTK_MENU_SHELL(m), it); }
	gtk_menu_item_set_submenu(GTK_MENU_ITEM(top), m); gtk_menu_shell_append(GTK_MENU_SHELL(bar), top); return top;
}
int main(int c, char **v)
{
	gtk_init(&c, &v);
	GtkWidget *w = gtk_window_new(GTK_WINDOW_TOPLEVEL), *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0), *bar = gtk_menu_bar_new();
	const char *f[] = {"New", "Quit", NULL}, *e[] = {"Copy", NULL}, *h[] = {"About", NULL};
	menu(bar, "File", f); menu(bar, "Edit", e); menu(bar, "Help", h);
	gtk_box_pack_start(GTK_BOX(box), bar, FALSE, FALSE, 0); gtk_container_add(GTK_CONTAINER(w), box);
	gtk_window_set_title(GTK_WINDOW(w), "menubar3"); gtk_window_set_default_size(GTK_WINDOW(w), 400, 200);
	g_signal_connect(w, "destroy", G_CALLBACK(gtk_main_quit), NULL); gtk_widget_show_all(w); gtk_main(); return 0;
}
