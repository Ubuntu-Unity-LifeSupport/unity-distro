/* titletest - 52fa72e ("Hide LibAdwaita title widget if title would show without subtitle and should not"):
   an AdwHeaderBar with a custom AdwWindowTitle (no subtitle) whose title first equals the window title, so
   gtk-nocsd should hide it (adw_header_bar_set_show_title FALSE, since the system title bar already shows that
   text). After 3 s the AdwWindowTitle's title is changed to a text that is not in the window title: should the
   header show it again?
   Prints show-title, the title widget's child-visible and mapped state at 1, 2, 4, 5 and 6 s, then quits.
   Mode argument:
     same    - start equal to the window title, change to a different text at 3 s (the case in question)
     differ  - start with a different text (control: should never be hidden)
     appname - start equal to the application name "titletest" (5f5acae), change at 3 s */
#include <adwaita.h>
#include <stdio.h>
#include <string.h>

static AdwHeaderBar *bar;
static AdwWindowTitle *title;
static GtkWindow *window;
static int ticks;

static gboolean tick(gpointer app) {
	ticks++;
	if (ticks == 3) {
		adw_window_title_set_title(title, "Changed text 42");
		printf("t=3s: title text set to \"Changed text 42\"\n");
	} else {
		GtkWidget *w = GTK_WIDGET(title);
		printf("t=%ds: show-title=%d child-visible=%d mapped=%d text=\"%s\" window-title=\"%s\"\n", ticks,
		       adw_header_bar_get_show_title(bar), gtk_widget_get_child_visible(w), gtk_widget_get_mapped(w),
		       adw_window_title_get_title(title), gtk_window_get_title(window));
	}
	fflush(stdout);
	if (ticks >= 6) {
		g_application_quit(G_APPLICATION(app));
		return G_SOURCE_REMOVE;
	}
	return G_SOURCE_CONTINUE;
}

static const char *mode = "same";

static void activate(GtkApplication *app, gpointer data) {
	(void) data;
	window = GTK_WINDOW(adw_application_window_new(app));
	gtk_window_set_title(window, "Document One");
	gtk_window_set_default_size(window, 480, 240);
	const char *start = strcmp(mode, "differ") == 0 ? "Something else" :
	                    strcmp(mode, "appname") == 0 ? "titletest" : "Document One";
	title = ADW_WINDOW_TITLE(adw_window_title_new(start, ""));
	bar = ADW_HEADER_BAR(adw_header_bar_new());
	adw_header_bar_set_title_widget(bar, GTK_WIDGET(title));
	GtkWidget *view = adw_toolbar_view_new();
	adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(view), GTK_WIDGET(bar));
	adw_toolbar_view_set_content(ADW_TOOLBAR_VIEW(view), gtk_label_new("content"));
	adw_application_window_set_content(ADW_APPLICATION_WINDOW(window), view);
	gtk_window_present(window);
	printf("mode %s: start text \"%s\", window title \"%s\"\n", mode, start, gtk_window_get_title(window));
	fflush(stdout);
	g_timeout_add_seconds(1, tick, app);
}

int main(int argc, char **argv) {
	if (argc > 1) mode = argv[1];
	g_set_application_name("titletest");
	AdwApplication *app = adw_application_new("org.example.TitleTest", G_APPLICATION_NON_UNIQUE);
	g_signal_connect(app, "activate", G_CALLBACK(activate), NULL);
	char *args[] = { argv[0], NULL };
	return g_application_run(G_APPLICATION(app), 1, args);
}
