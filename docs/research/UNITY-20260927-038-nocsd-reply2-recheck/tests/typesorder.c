/* typesorder - gtk-nocsd sees GTK4 first in a GetTypes=false call.
   1. a GObject is created before GTK is loaded (gtk-nocsd's g_object_new
      hook runs GetReferences(true) with no GTK: GotTypes becomes true);
   2. GTK4 is dlopen'ed and its GtkWindow type registered through dlsym
      (gtk-nocsd's g_type_register_static_simple hook: GetReferences(false),
      which records GTK version 4 but fetches no types);
   3. GTK is initialised and a window created (GetReferences(true) again).
   Then gdb reads GTKNoCSDGTKWindow: 0 means the types were never fetched. */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <glib-object.h>
int main(void)
{
	if (getenv("SKIP_EARLY_OBJECT") == NULL) {
		GObject *o = g_object_new(G_TYPE_OBJECT, NULL);
		g_object_unref(o);
	}
	void *gtk = dlopen("libgtk-4.so.1", RTLD_NOW | RTLD_GLOBAL);
	if (!gtk) { fprintf(stderr, "no gtk\n"); return 2; }
	GType (*window_type)(void) = dlsym(gtk, "gtk_window_get_type");
	void (*init)(void) = dlsym(gtk, "gtk_init");
	void *(*window_new)(void) = dlsym(gtk, "gtk_window_new");
	GType t = window_type();
	init();
	void *w = window_new();
	printf("GtkWindow type %lu, window %p\n", (unsigned long)t, w);
	fflush(stdout);
	return 0;
}
