// dialogtitle.c - reproducer for gtk-nocsd 8f076dd (GTKNoCSDLabelChange)
//
// dialog: an AdwDialog in its own window (no parent) without a title, a header
//         bar with a "title" label as its title widget, and an AdwStatusPage as content. Criticals are
//         fatal, as in Epiphany. With 8f076dd..main preloaded this aborts in
//         gtk_widget_get_preferred_size(NULL) and titles the window with the
//         status page text.
// clock:  a window whose header title widget is a "title" label that changes
//         every 0.4 s, like GNOME Mahjongg's clock; prints the window title.
//
// Build: cc dialogtitle.c $(pkg-config --cflags --libs libadwaita-1)
#include <adwaita.h>

static const char *Mode;
static int Ticks;

static gboolean Tick(gpointer Data) {
	GtkWidget *Label = Data;
	char Text[32];
	g_snprintf(Text, sizeof Text, "00:%02d", ++Ticks);
	gtk_label_set_text(GTK_LABEL(Label), Text);
	GtkWindow *Window = GTK_WINDOW(gtk_widget_get_root(Label));
	const char *Title = gtk_window_get_title(Window);
	g_print("clock: label %s, window title '%s', label opacity %.0f, visible %d\n",
		Text, Title ? Title : "(null)", gtk_widget_get_opacity(Label),
		gtk_widget_get_visible(Label));
	if (Ticks == 4) {
		g_application_quit(g_application_get_default());
		return G_SOURCE_REMOVE;
	}
	return G_SOURCE_CONTINUE;
}

static gboolean Report(gpointer Data) {
	GList *Windows = gtk_window_list_toplevels();
	for (GList *E = Windows; E != NULL; E = E->next) {
		const char *Title = gtk_window_get_title(E->data);
		g_print("dialog: window %s title '%s'\n", G_OBJECT_TYPE_NAME(E->data),
			Title ? Title : "(null)");
	}
	g_list_free(Windows);
	g_application_quit(g_application_get_default());
	return G_SOURCE_REMOVE;
}

static void Activate(GtkApplication *Application) {
	GtkWidget *Window = adw_application_window_new(Application);
	gtk_window_set_default_size(GTK_WINDOW(Window), 600, 400);
	GtkWidget *View = adw_toolbar_view_new();
	GtkWidget *Header = adw_header_bar_new();
	adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(View), Header);

	if (g_strcmp0(Mode, "clock") == 0) {
		GtkWidget *Label = gtk_label_new("00:00");
		gtk_widget_add_css_class(Label, "title");
		adw_header_bar_set_title_widget(ADW_HEADER_BAR(Header), Label);
		adw_application_window_set_content(ADW_APPLICATION_WINDOW(Window), View);
		gtk_window_present(GTK_WINDOW(Window));
		g_timeout_add(400, Tick, Label);
		return;
	}

	gtk_window_set_title(GTK_WINDOW(Window), "Main");
	adw_application_window_set_content(ADW_APPLICATION_WINDOW(Window), View);
	gtk_window_present(GTK_WINDOW(Window));

	AdwDialog *Dialog = adw_dialog_new();
	adw_dialog_set_content_width(Dialog, 400);
	adw_dialog_set_content_height(Dialog, 300);
	GtkWidget *DialogView = adw_toolbar_view_new();
	// Like Epiphany's EphyDataView: the header shows a label of its own, the
	// dialog has no title
	GtkWidget *DialogHeader = adw_header_bar_new();
	GtkWidget *HeaderLabel = gtk_label_new("Passwords");
	gtk_widget_add_css_class(HeaderLabel, "title");
	adw_header_bar_set_title_widget(ADW_HEADER_BAR(DialogHeader), HeaderLabel);
	adw_toolbar_view_add_top_bar(ADW_TOOLBAR_VIEW(DialogView), DialogHeader);
	GtkWidget *Status = adw_status_page_new();
	adw_status_page_set_title(ADW_STATUS_PAGE(Status), "No Passwords Found");
	adw_toolbar_view_set_content(ADW_TOOLBAR_VIEW(DialogView), Status);
	adw_dialog_set_child(Dialog, DialogView);
	adw_dialog_present(Dialog, NULL);
	g_timeout_add(1500, Report, NULL);
}

int main(int argc, char **argv) {
	Mode = argc > 1 ? argv[1] : "dialog";
	g_log_set_always_fatal(G_LOG_LEVEL_CRITICAL);
	AdwApplication *Application = adw_application_new("org.example.DialogTitle",
		G_APPLICATION_NON_UNIQUE);
	g_signal_connect(Application, "activate", G_CALLBACK(Activate), NULL);
	return g_application_run(G_APPLICATION(Application), 1, argv);
}
