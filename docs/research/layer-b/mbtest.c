/* Minimal GTK4 app that sets an application menubar.
   Question: does GTK4 still export it on the session bus and advertise it
   through _GTK_MENUBAR_OBJECT_PATH, and does the Unity panel pick it up? */
#include <gtk/gtk.h>

static void on_activate(GtkApplication *app, gpointer d) {
  GMenu *bar  = g_menu_new();
  GMenu *file = g_menu_new();
  g_menu_append(file, "Open Marker", "app.marker");
  g_menu_append(file, "Quit", "app.quit");
  g_menu_append_submenu(bar, "TestFile", G_MENU_MODEL(file));
  GMenu *help = g_menu_new();
  g_menu_append(help, "About Marker", "app.about");
  g_menu_append_submenu(bar, "TestHelp", G_MENU_MODEL(help));

  gtk_application_set_menubar(app, G_MENU_MODEL(bar));

  GtkWidget *w = gtk_application_window_new(app);
  gtk_window_set_title(GTK_WINDOW(w), "mbtest");
  gtk_window_set_default_size(GTK_WINDOW(w), 420, 220);
  gtk_window_present(GTK_WINDOW(w));
}

int main(int argc, char **argv) {
  GtkApplication *app = gtk_application_new("org.unitydistro.mbtest",
                                            G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect(app, "activate", G_CALLBACK(on_activate), NULL);
  return g_application_run(G_APPLICATION(app), argc, argv);
}
