/*
 * localplugin.c - a GTK4 plugin opened RTLD_LOCAL by a host that links neither GTK nor GLib, so libgtk-4 is not
 * in the global scope (UNITY-20261013-013, Design Challenger test 2). The plugin's own call to
 * gtk_widget_action_set_enabled() binds to the preloaded libunity-gtk4-menu, whose "next" setter is then not found
 * by RTLD_NEXT. If the wrapper does not reach the real setter, the action stays enabled.
 *
 *   cc -shared -fPIC -o localplugin.so localplugin.c $(pkg-config --cflags --libs gtk4)
 *   cc -o localhost localplugin.c -DHOST -ldl
 *   ./localhost ./localplugin.so     (under a display)
 *
 * Prints "activations: N" for: disable, activate, enable, activate. N = 1 is right; 2 means the disable was lost.
 */
#ifdef HOST
#include <dlfcn.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	void *p = dlopen(argc > 1 ? argv[1] : "./localplugin.so", RTLD_NOW | RTLD_LOCAL);
	if (p == NULL) {
		fprintf(stderr, "dlopen: %s\n", dlerror());
		return 2;
	}
	int (*run)(void) = (int (*)(void))dlsym(p, "plugin_run");
	if (run == NULL) {
		fprintf(stderr, "no plugin_run\n");
		return 2;
	}
	printf("libgtk-4 in the global scope: %s\n", dlsym(RTLD_DEFAULT, "gtk_init") ? "yes" : "no");
	int n = run();
	printf("activations: %d\n", n);
	return n == 1 ? 0 : 1;
}
#else
#include <gtk/gtk.h>

static int activations;

#define TEST_TYPE_WIDGET (test_widget_get_type())
G_DECLARE_FINAL_TYPE(TestWidget, test_widget, TEST, WIDGET, GtkWidget)
struct _TestWidget { GtkWidget parent; };
G_DEFINE_TYPE(TestWidget, test_widget, GTK_TYPE_WIDGET)

static void act(GtkWidget *w, const char *name, GVariant *param)
{
	activations++;
}

static void test_widget_class_init(TestWidgetClass *klass)
{
	gtk_widget_class_install_action(GTK_WIDGET_CLASS(klass), "t.act", NULL, act);
}

static void test_widget_init(TestWidget *self)
{
}

int plugin_run(void)
{
	gtk_init();
	GtkWidget *w = g_object_ref_sink(g_object_new(TEST_TYPE_WIDGET, NULL));
	gtk_widget_action_set_enabled(w, "t.act", FALSE);
	gtk_widget_activate_action(w, "t.act", NULL);
	gtk_widget_action_set_enabled(w, "t.act", TRUE);
	gtk_widget_activate_action(w, "t.act", NULL);
	g_object_unref(w);
	return activations;
}
#endif
