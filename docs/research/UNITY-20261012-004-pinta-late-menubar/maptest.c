/*
 * maptest.c - the cost of the map shim in an application without a menu (UNITY-20261012-004, design item 10). An
 * application window with a header bar and no menu (so the library keeps it waiting and installs its map shims),
 * then one GtkMenuButton without a model, hidden and shown N times; each show maps it, each hide unmaps it. Prints
 * the wall time of the N cycles. Run once with the library preloaded and once without, and compare.
 *
 *   cc -O2 -o maptest maptest.c $(pkg-config --cflags --libs gtk4)
 *   ./maptest [N]
 */
#include <gtk/gtk.h>
#include <stdio.h>
#include <stdlib.h>

static int cycles = 10000;

static void spin(int ms)
{
	gint64 end = g_get_monotonic_time() + (gint64)ms * 1000;
	while (g_get_monotonic_time() < end)
		g_main_context_iteration(NULL, FALSE);
}

static void activate(GtkApplication *app, gpointer data)
{
	GtkWidget *window = gtk_application_window_new(app);
	GtkWidget *header = gtk_header_bar_new();
	gtk_window_set_titlebar(GTK_WINDOW(window), header);
	gtk_window_present(GTK_WINDOW(window));
	spin(500);

	GtkWidget *b = gtk_menu_button_new();
	gtk_header_bar_pack_end(GTK_HEADER_BAR(header), b);
	spin(500);
	printf("button mapped before the loop: %d\n", gtk_widget_get_mapped(b));

	int mapped = 0;
	gint64 t0 = g_get_monotonic_time();
	for (int i = 0; i < cycles; i++) {
		gtk_widget_set_visible(b, FALSE);
		gtk_widget_set_visible(b, TRUE);
		mapped += gtk_widget_get_mapped(b);
	}
	gint64 t1 = g_get_monotonic_time();
	spin(300);	/* let any idle look the library scheduled run */
	printf("cycles %d, mapped after show %d, loop %.1f ms (%.2f us per cycle)\n", cycles, mapped,
	       (t1 - t0) / 1000.0, (double)(t1 - t0) / cycles);
	fflush(stdout);
	gtk_window_destroy(GTK_WINDOW(window));
}

int main(int argc, char **argv)
{
	if (argc > 1)
		cycles = atoi(argv[1]);
	GtkApplication *app = gtk_application_new("org.unitydistro.MapTest", G_APPLICATION_DEFAULT_FLAGS);
	g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);
	int rc = g_application_run(G_APPLICATION(app), 1, argv);
	g_object_unref(app);
	return rc;
}
