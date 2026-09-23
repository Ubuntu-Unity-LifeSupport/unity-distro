/* Mimics how yelp builds its menus: the menu button is given a GtkPopoverMenu
   with gtk_menu_button_set_popover(), so gtk_menu_button_get_menu_model()
   returns NULL and a naive search finds nothing. The model is still reachable
   through gtk_popover_menu_get_menu_model(). */
#include <gtk/gtk.h>

static void on_activate(GtkApplication *app, gpointer d) {
  GMenu *m = g_menu_new();
  GMenu *s1 = g_menu_new();
  g_menu_append(s1, "Popover Item One", "app.one");
  g_menu_append(s1, "Popover Item Two", "app.two");
  g_menu_append_section(m, NULL, G_MENU_MODEL(s1));

  GtkWidget *popover = gtk_popover_menu_new_from_model(G_MENU_MODEL(m));
  GtkWidget *button  = gtk_menu_button_new();
  gtk_menu_button_set_popover(GTK_MENU_BUTTON(button), popover);
  gtk_menu_button_set_icon_name(GTK_MENU_BUTTON(button), "open-menu-symbolic");

  GtkWidget *header = gtk_header_bar_new();
  gtk_header_bar_pack_end(GTK_HEADER_BAR(header), button);

  GtkWidget *w = gtk_application_window_new(app);
  gtk_window_set_titlebar(GTK_WINDOW(w), header);
  gtk_window_set_title(GTK_WINDOW(w), "popovertest");
  gtk_window_set_default_size(GTK_WINDOW(w), 420, 220);
  gtk_window_present(GTK_WINDOW(w));
}

int main(int argc, char **argv) {
  GtkApplication *app = gtk_application_new("org.unitydistro.popovertest",
                                            G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect(app, "activate", G_CALLBACK(on_activate), NULL);
  return g_application_run(G_APPLICATION(app), argc, argv);
}
