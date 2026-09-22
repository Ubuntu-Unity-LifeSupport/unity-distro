/* Same as mbtest, but the menubar is attached 6 seconds AFTER the window is
   shown - the situation any external shim would face, since it can only act
   once the application has finished building its UI. */
#include <gtk/gtk.h>

static GtkApplication *theapp;

static gboolean attach_late(gpointer d) {
  GMenu *bar = g_menu_new();
  GMenu *m   = g_menu_new();
  g_menu_append(m, "Late Item", "app.x");
  g_menu_append_submenu(bar, "LateMenu", G_MENU_MODEL(m));
  gtk_application_set_menubar(theapp, G_MENU_MODEL(bar));
  g_print("menubar attached late\n");
  return G_SOURCE_REMOVE;
}

static void on_activate(GtkApplication *app, gpointer d) {
  GtkWidget *w = gtk_application_window_new(app);
  gtk_window_set_title(GTK_WINDOW(w), "latetest");
  gtk_window_set_default_size(GTK_WINDOW(w), 420, 220);
  gtk_window_present(GTK_WINDOW(w));
  g_timeout_add_seconds(6, attach_late, NULL);
}

int main(int argc, char **argv) {
  theapp = gtk_application_new("org.unitydistro.latetest", G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect(theapp, "activate", G_CALLBACK(on_activate), NULL);
  return g_application_run(G_APPLICATION(theapp), argc, argv);
}
