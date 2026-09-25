// GTK3 module: after 6 s, list every GtkMenuButton in every toplevel with
// what its menu is built from (GMenuModel, GtkMenu, hand-made popover)
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>

static GtkWidget *Win;
static int Ok, Dead;
static void Acts(GMenuModel *M, int D) {
	int I, n = g_menu_model_get_n_items(M);
	for (I = 0; I < n && D < 8; I++) {
		gchar *A = NULL;
		GMenuModel *C = g_menu_model_get_item_link(M, I, "section");
		if (!C) C = g_menu_model_get_item_link(M, I, "submenu");
		if (C) { Acts(C, D + 1); g_object_unref(C); continue; }
		if (!g_menu_model_get_item_attribute(M, I, "action", "s", &A)) { printf("PROBE3A noaction\n"); continue; }
		const char *Dot = strchr(A, '.');
		GActionGroup *G = NULL;
		if (Dot && strncmp(A, "app.", 4) == 0) G = G_ACTION_GROUP(g_application_get_default());
		if (Dot && strncmp(A, "win.", 4) == 0) G = G_ACTION_GROUP(Win);
		int E = G && g_action_group_has_action(G, Dot + 1);
		E ? Ok++ : Dead++;
		printf("PROBE3A %s %s\n", E ? "exported" : "NOT", A);
		g_free(A);
	}
}
static int Count(GMenuModel *M, int D) {
	int N = 0, I, n = g_menu_model_get_n_items(M);
	for (I = 0; I < n && D < 8; I++) {
		GMenuModel *C = g_menu_model_get_item_link(M, I, "section");
		if (!C) C = g_menu_model_get_item_link(M, I, "submenu");
		if (C) { N += Count(C, D + 1); g_object_unref(C); } else N++;
	}
	return N;
}
static int Leaves(GtkWidget *W, const char *T) {
	int N = 0;
	if (g_type_is_a(G_OBJECT_TYPE(W), g_type_from_name(T))) N++;
	if (GTK_IS_CONTAINER(W)) {
		GList *L = gtk_container_get_children(GTK_CONTAINER(W));
		for (GList *E = L; E; E = E->next) N += Leaves(E->data, T);
		g_list_free(L);
	}
	return N;
}
static void Walk(GtkWidget *W, gpointer D) {
	if (GTK_IS_MENU_BUTTON(W)) {
		GtkMenuButton *B = GTK_MENU_BUTTON(W);
		GMenuModel *M = gtk_menu_button_get_menu_model(B);
		GtkPopover *P = gtk_menu_button_get_popover(B);
		GtkMenu *U = gtk_menu_button_get_popup(B);
		const char *icon = NULL;
		GtkWidget *img = gtk_bin_get_child(GTK_BIN(W));
		if (img && GTK_IS_IMAGE(img)) gtk_image_get_icon_name(GTK_IMAGE(img), &icon, NULL);
		if (M && icon && strcmp(icon, "open-menu-symbolic") == 0 || (M && Count(M,0) > 8)) {
			Win = gtk_widget_get_toplevel(W); Ok = Dead = 0; Acts(M, 0);
			printf("PROBE3S %s main exported=%d not=%d\n", g_get_prgname(), Ok, Dead);
		}
		printf("PROBE3 %s button icon=%s model=%s(%d) popover=%s modelbuttons=%d popup=%s visible=%d\n",
			g_get_prgname(), icon ? icon : "-",
			M ? "yes" : "no", M ? Count(M, 0) : 0,
			P ? G_OBJECT_TYPE_NAME(P) : "-",
			P ? Leaves(GTK_WIDGET(P), "GtkModelButton") : 0,
			U ? "GtkMenu" : "-", gtk_widget_get_visible(W));
	}
	if (GTK_IS_CONTAINER(W)) gtk_container_forall(GTK_CONTAINER(W), Walk, D);
}
static gboolean Probe(gpointer D) {
	GList *L = gtk_window_list_toplevels();
	for (GList *E = L; E; E = E->next) {
		GtkWidget *T = E->data;
		if (!gtk_widget_get_visible(T)) continue;
		printf("PROBE3 %s window %s appwin=%d\n", g_get_prgname(), G_OBJECT_TYPE_NAME(T),
			GTK_IS_APPLICATION_WINDOW(T));
		Walk(T, NULL);
	}
	g_list_free(L);
	GApplication *A = g_application_get_default();
	if (A && GTK_IS_APPLICATION(A))
		printf("PROBE3 %s appmenu=%d menubar=%d\n", g_get_prgname(),
			gtk_application_get_app_menu(GTK_APPLICATION(A)) != NULL,
			gtk_application_get_menubar(GTK_APPLICATION(A)) != NULL);
	fflush(stdout);
	return FALSE;
}
G_MODULE_EXPORT void gtk_module_init(gint *c, gchar ***v) { g_timeout_add(6000, Probe, NULL); }
