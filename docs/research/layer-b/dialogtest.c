/* Does hooking GtkWindow::realize disturb dialogs? The hook fires for every
   GtkWindow, and a dialog is one. Opens a main window with a menu, then an
   AlertDialog and an AboutDialog on top of it. */
#include <gtk/gtk.h>

static GtkWindow *mainwin;

static gboolean open_dialogs(gpointer d) {
  GtkAlertDialog *alert = gtk_alert_dialog_new("Dialog under the shim");
  gtk_alert_dialog_set_detail(alert, "If this renders, realize survived.");
  gtk_alert_dialog_show(alert, mainwin);
  g_object_unref(alert);

  gtk_show_about_dialog(mainwin, "program-name", "dialogtest",
                        "version", "1.0", "comments",
                        "About dialog, also a GtkWindow.", NULL);
  return G_SOURCE_REMOVE;
}

static void on_activate(GtkApplication *app, gpointer d) {
  GMenu *m = g_menu_new();
  GMenu *s = g_menu_new();
  g_menu_append(s, "Item", "app.x");
  g_menu_append_section(m, NULL, G_MENU_MODEL(s));

  GtkWidget *button = gtk_menu_button_new();
  gtk_menu_button_set_menu_model(GTK_MENU_BUTTON(button), G_MENU_MODEL(m));
  GtkWidget *header = gtk_header_bar_new();
  gtk_header_bar_pack_end(GTK_HEADER_BAR(header), button);

  GtkWidget *w = gtk_application_window_new(app);
  gtk_window_set_titlebar(GTK_WINDOW(w), header);
  gtk_window_set_title(GTK_WINDOW(w), "dialogtest");
  gtk_window_set_default_size(GTK_WINDOW(w), 480, 260);
  mainwin = GTK_WINDOW(w);
  gtk_window_present(GTK_WINDOW(w));
  g_timeout_add_seconds(3, open_dialogs, NULL);
}

int main(int argc, char **argv) {
  GtkApplication *app = gtk_application_new("org.unitydistro.dialogtest",
                                            G_APPLICATION_DEFAULT_FLAGS);
  g_signal_connect(app, "activate", G_CALLBACK(on_activate), NULL);
  return g_application_run(G_APPLICATION(app), argc, argv);
}
