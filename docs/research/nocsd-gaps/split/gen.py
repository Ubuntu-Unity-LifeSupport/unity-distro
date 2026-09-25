#!/usr/bin/env python3
"""gen.py MAIN.c MAIN_README OUT.c OUT_README PARTS
Build gtk-nocsd's GTK-NoCSD.c and README.md with the global menu split into
parts: the base (always), A = model cleaning and class-action proxies,
B = realize replacement, C = following gtk-shell-shows-menubar.
PARTS is a string such as "", "A", "AB", "ABC"."""
import json, re, sys

main_c, main_readme, out_c, out_readme, parts = sys.argv[1:6]
P = set(parts)
HERE = __file__.rsplit('/', 1)[0]
F = json.load(open(HERE + '/funcs.json'))
J = json.load(open(HERE + '/parts.json'))
BASE, A, DEC, GRP = J['BASE'], J['A'], J['dec'], J['grp']
NEW = {
    'g_signal_handler_disconnect': ('void (*o_g_signal_handler_disconnect) (gpointer, gulong) = NULL;', 'gobject'),
    'g_action_group_has_action': ('gboolean (*o_g_action_group_has_action) (GActionGroup *, const gchar *) = NULL;', 'gio'),
    'g_action_group_get_action_enabled': ('gboolean (*o_g_action_group_get_action_enabled) (GActionGroup *, const gchar *) = NULL;', 'gio'),
    'g_action_group_get_action_parameter_type': ('const GVariantType * (*o_g_action_group_get_action_parameter_type) (GActionGroup *, const gchar *) = NULL;', 'gio'),
    'g_action_group_get_action_state': ('GVariant * (*o_g_action_group_get_action_state) (GActionGroup *, const gchar *) = NULL;', 'gio'),
    'g_action_map_remove_action': ('void (*o_g_action_map_remove_action) (GActionMap *, const gchar *) = NULL;', 'gio'),
}
BASE.append('g_menu_remove')
for n in ('g_menu_item_new_from_model', 'g_menu_append_item'):
    A.remove(n)
    BASE.append(n)
DEC['g_menu_remove'] = 'void (*o_g_menu_remove) (GMenu *, gint) = NULL;'
GRP['g_menu_remove'] = 'gio'
for n, (d, g) in NEW.items():
    DEC[n] = d
    GRP[n] = g
    A.append(n)


def pick(text):
    """Keep //@@X ... //@@/X blocks when X in P, //@@!X blocks when X not in P."""
    out, stack = [], []
    for line in text.split('\n'):
        m = re.match(r'\s*//@@(!?)([ABCD])$', line)
        e = re.match(r'\s*//@@/(!?)([ABCD])$', line)
        if m:
            stack.append((m.group(1) == '!', m.group(2)))
            continue
        if e:
            stack.pop()
            continue
        keep = all((x not in P) if neg else (x in P) for neg, x in stack)
        if keep:
            out.append(line)
    return '\n'.join(out)


def f(name, old=None, new=None):
    body = F[name]
    if old is not None:
        assert old in body, (name, old[:40])
        body = body.replace(old, new)
    return body


def loads(names, lib_group, indent='\t'):
    return ''.join(f'{indent}LOAD_SYMBOL(Library, {n});\n' for n in names
                   if GRP[n] == lib_group and n != 'gtk_widget_action_set_enabled')


def needed(names):
    return ''.join(f'\t\t(void *) o_{n},\n' for n in names
                   if n != 'gtk_widget_action_set_enabled').rstrip(',\n') + '\n'


BASE_TYPES = ['gtk_menu_button_get_type', 'gtk_popover_menu_get_type',
              'gtk_popover_menu_bar_get_type']
base_funcs = [n for n in BASE if n not in BASE_TYPES]

GROUPS = open(HERE + '/groups.c').read()
INSERT_HOOK = open(HERE + '/insert-hook.c').read()

section = f"""// Global menu: with GTK_NOCSD_GLOBAL_MENU=1 the main menu of a GTK4 header
// bar is set as the application's menubar, which GTK exports for a global
// menu
//@@C
// It is only done while the shell shows the menubar (gtk-shell-shows-menubar),
// elsewhere nothing reads it
//@@/C

// A menu found in a window, and how likely it is to be the main menu
struct GTKNoCSDMenuCandidate {{
	GtkWidget *Owner;
	GMenuModel *Model;
	bool Shown;
	bool Primary;
	int Score;
}};

// Every menu found in a window
struct GTKNoCSDMenuCandidates {{
	struct GTKNoCSDMenuCandidate List[32];
	size_t Count;
}};
//@@A

// A class action made reachable over D-Bus, activated from its menu's owner
struct GTKNoCSDMenuProxy {{
	GtkWidget *Owner;
	GtkWidget *Holder;
	gchar *Name;
}};
//@@/A

// Whether the functions of the global menu were fetched, and all were found
bool GTKNoCSDMenuPrepared = false, GTKNoCSDMenuReady = false;
//@@A
bool GTKNoCSDMenuProxyReady = false;
//@@/A
//@@B
bool GTKNoCSDMenuHooked = false;
//@@/B
//@@C
bool GTKNoCSDMenuWatching = false;
//@@/C

// The menubar set by the library, to tell it apart from the application's
GMenuModel *GTKNoCSDMenubar = NULL;
//@@B

// The original realize of GtkWindow and GtkApplicationWindow
void (*GTKNoCSDWindowRealize)(GtkWidget *) = NULL;
void (*GTKNoCSDApplicationWindowRealize)(GtkWidget *) = NULL;
//@@/B

{f('GTKNoCSDMenuShown')}
{f('GTKNoCSDMenuReachableItems')}
{f('GTKNoCSDMenuAddCandidate')}
{f('GTKNoCSDMenuCollect')}
{f('GTKNoCSDMenuFind')}
{f('GTKNoCSDMenuLabel')}
void GTKNoCSDGetMenuSymbols(void) {{
	// Fetch the functions the global menu needs

	void *Library = GTKNoCSDGetLibrary("libgobject-2.0.so.0", true);
{loads(base_funcs, 'gobject')}	dlclose(Library);

	Library = GTKNoCSDGetLibrary("libgio-2.0.so.0", true);
{loads(base_funcs, 'gio')}	dlclose(Library);

	Library = GTKNoCSDGetLibrary(GTKNoCSDNewGTKName, true);
{loads(BASE, 'gtk4')}	dlclose(Library);

	GET_TYPE(GTKNoCSDGTKMenuButton, gtk_menu_button_get_type);
	GET_TYPE(GTKNoCSDGTKPopoverMenu, gtk_popover_menu_get_type);
	GET_TYPE(GTKNoCSDGTKPopoverMenuBar, gtk_popover_menu_bar_get_type);
}}
//@@A

void GTKNoCSDGetMenuProxySymbols(void) {{
	// Fetch the functions for cleaning the menu and proxying class actions

	void *Library = GTKNoCSDGetLibrary("libgobject-2.0.so.0", true);
{loads(A, 'gobject')}	dlclose(Library);

	Library = GTKNoCSDGetLibrary("libgio-2.0.so.0", true);
{loads(A, 'gio')}	dlclose(Library);

	Library = GTKNoCSDGetLibrary(GTKNoCSDNewGTKName, true);
{loads(A, 'gtk4')}	dlclose(Library);

	void *Needed[] = {{
{needed(A)}	}};
	for (size_t Index = 0; Index < sizeof(Needed) / sizeof(Needed[0]);
		++Index) {{
		if (Needed[Index] == NULL) {{
			return;
		}}
	}}

	GTKNoCSDMenuProxyReady = true;
}}
//@@/A

void GTKNoCSDMenuPrepare(void) {{
	// Fetch the functions of the global menu once, when it is first needed

	if (GTKNoCSDMenuPrepared) {{
		return;
	}}
	GTKNoCSDMenuPrepared = true;

	GTKNoCSDGetMenuSymbols();
	void *Needed[] = {{
{needed(base_funcs)}	}};
	for (size_t Index = 0; Index < sizeof(Needed) / sizeof(Needed[0]);
		++Index) {{
		if (Needed[Index] == NULL) {{
			return;
		}}
	}}
	if (GTKNoCSDGTKMenuButton == 0 || GTKNoCSDGTKPopoverMenu == 0 ||
		GTKNoCSDGTKPopoverMenuBar == 0) {{
		return;
	}}

	GTKNoCSDMenuReady = true;
//@@A
	GTKNoCSDGetMenuProxySymbols();
//@@/A
}}
//@@A

{f('GTKNoCSDMenuKey')}
{f('GTKNoCSDMenuProxyActivate')}
{f('GTKNoCSDMenuProxyFree')}
{f('GTKNoCSDMenuFindClassAction')}
{f('GTKNoCSDMenuPropertyState')}
{f('GTKNoCSDMenuPropertyNotified')}
{f('GTKNoCSDMenuProxyChangeState')}
{GROUPS}{f('GTKNoCSDMenuProxyFor', '''	if (Holder == NULL) {
		return NULL;
	}''', '''	if (Holder == NULL) {
		return GTKNoCSDMenuGroupProxyFor(Name, Map);
	}''')}
{f('GTKNoCSDMenuClean')}//@@/A
//@@C

{f('GTKNoCSDMenuShellChanged')}//@@/C

void GTKNoCSDMenuKeep(GMenuModel *Menubar) {{
	// Remember the menubar set by the library. A withdrawn one may still
	// live, it must not clear the new one

	if (GTKNoCSDMenubar != NULL) {{
		o_g_object_remove_weak_pointer((GObject *) GTKNoCSDMenubar,
			(gpointer *) &GTKNoCSDMenubar);
	}}
	GTKNoCSDMenubar = Menubar;
	o_g_object_add_weak_pointer((GObject *) Menubar,
		(gpointer *) &GTKNoCSDMenubar);
}}
//@@D

""" + open(HERE + '/deferred.c').read() + f"""//@@/D

void GTKNoCSDMenuAttach(GtkWindow *Window) {{
	// Set the main menu of the window as the application's menubar

	if (!GTKNoCSDGlobalMenu || GTKNoCSDGTKVersion != 4) {{
		return;
	}}
	GTKNoCSDMenuPrepare();
	if (!GTKNoCSDMenuReady) {{
		return;
	}}

	// WARNING: Own call
	GtkApplication *Application = gtk_window_get_application(Window);
	if (Application == NULL) {{
		return;
	}}
//@@C

	// Only where the shell shows the menubar, elsewhere nothing reads it
	gboolean ShellShowsMenubar = FALSE;
	o_g_object_get((GObject *) o_gtk_settings_get_default(),
		"gtk-shell-shows-menubar", &ShellShowsMenubar, NULL);
	if (!ShellShowsMenubar) {{
		return;
	}}
//@@/C

	GMenuModel *Existing = o_gtk_application_get_menubar(Application);
	if (Existing != NULL && Existing != GTKNoCSDMenubar) {{
		return;
	}}
//@@D

	// A menu may appear after its window (Pinta adds its menu buttons after
	// presenting it). Set an empty menubar now, so GTK announces it when the
	// window is realized, and fill it once the menu is found
	if (Existing == NULL) {{
		GMenu *Menubar = o_g_menu_new();
		o_gtk_application_set_menubar(Application, (GMenuModel *) Menubar);
		GTKNoCSDMenuKeep((GMenuModel *) Menubar);
		o_g_object_unref((GObject *) Menubar);
		GTKNoCSDMenuFilled = false;
	}}
	if (!GTKNoCSDMenuFill(Window)) {{
		GTKNoCSDMenuRetry(Window);
	}}
//@@/D
//@@!D

	GtkWidget *Owner = NULL;
	GMenuModel *Model = GTKNoCSDMenuFind(Window, &Owner);
	if (Model == NULL) {{
		return;
	}}
//@@A

	// The menubar belongs to the application, but window actions to the
	// focused window, so another window only needs the stand-ins
	GActionMap *Map = GTKNoCSDGtkApplicatonWindow((GObject *) Window) ?
		(GActionMap *) Window : NULL;
	GMenuModel *Cleaned = GTKNoCSDMenuProxyReady ?
		GTKNoCSDMenuClean(Model, 0, Owner, Map) :
		(GMenuModel *) o_g_object_ref((GObject *) Model);
//@@/A
//@@!A
	GMenuModel *Cleaned = (GMenuModel *) o_g_object_ref((GObject *) Model);
//@@/!A
	if (Existing != NULL) {{
		o_g_object_unref((GObject *) Cleaned);
		return;
	}}

	gchar *Label = GTKNoCSDMenuLabel(Application);
	GMenu *Menubar = o_g_menu_new();
	o_g_menu_append_submenu(Menubar, Label, Cleaned);
	o_g_free(Label);
	o_g_object_unref((GObject *) Cleaned);
	o_gtk_application_set_menubar(Application, (GMenuModel *) Menubar);

	GTKNoCSDMenuKeep((GMenuModel *) Menubar);
	o_g_object_unref((GObject *) Menubar);
//@@/!D
//@@C

	// Take it back if the shell stops showing it
	if (!GTKNoCSDMenuWatching) {{
		GTKNoCSDMenuWatching = true;
		o_g_signal_connect_object(o_gtk_settings_get_default(),
			"notify::gtk-shell-shows-menubar",
			(GCallback) GTKNoCSDMenuShellChanged, Application, 0);
	}}
//@@/C
}}
//@@B

{f('GTKNoCSDMenuWindowRealize')}
{f('GTKNoCSDMenuApplicationWindowRealize')}
{f('GTKNoCSDMenuHookClass')}
void GTKNoCSDMenuHook(void) {{
	// Hook GTK4 windows once GTK4 and its types are known. A window shown
	// with gtk_window_present gets its menu there; one that is only made
	// visible, or shown by its parent, passes through nothing of ours before
	// it is realized, so realize is replaced in the window classes

	if (GTKNoCSDMenuHooked || !GTKNoCSDGlobalMenu ||
		GTKNoCSDGTKVersion != 4 || GTKNoCSDGTKWindow == 0 ||
		GTKNoCSDGTKApplicationWindow == 0) {{
		return;
	}}
	GTKNoCSDMenuHooked = true;

	GTKNoCSDMenuPrepare();
	if (!GTKNoCSDMenuReady) {{
		return;
	}}
	GTKNoCSDMenuHookClass(GTKNoCSDGTKWindow, &GTKNoCSDWindowRealize,
		GTKNoCSDMenuWindowRealize);
	GTKNoCSDMenuHookClass(GTKNoCSDGTKApplicationWindow,
		&GTKNoCSDApplicationWindowRealize,
		GTKNoCSDMenuApplicationWindowRealize);
}}
//@@/B
//@@A

{f('gtk_widget_action_set_enabled', 'if (!GTKNoCSDMenuReady ||', 'if (!GTKNoCSDMenuProxyReady ||')}
{INSERT_HOOK}//@@/A

"""

s = open(main_c).read()


def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


rep("GTKNoCSDNoCSS = false, GTKNoCSDNoGTK3 = false, GTKNoCSDNoGTK4 = false;",
    "GTKNoCSDNoCSS = false, GTKNoCSDNoGTK3 = false, GTKNoCSDNoGTK4 = false,\n\tGTKNoCSDGlobalMenu = false;")
rep("\tGET_VARIABLE(GTKNoCSDNoGTK4, GTK_NOCSD_NO_GTK4);\n",
    "\tGET_VARIABLE(GTKNoCSDNoGTK4, GTK_NOCSD_NO_GTK4);\n\tGET_VARIABLE(GTKNoCSDGlobalMenu, GTK_NOCSD_GLOBAL_MENU);\n")
rep("GType GTKNoCSDGTKButton = 0;\n",
    "GType GTKNoCSDGTKButton = 0;\nGType GTKNoCSDGTKMenuButton = 0;\nGType GTKNoCSDGTKPopoverMenu = 0;\nGType GTKNoCSDGTKPopoverMenuBar = 0;\n")
decls = [DEC[n] for n in BASE] + ([DEC[n] for n in A] if 'A' in P else [])
rep("// This is needed by an unavoidable GTK macros for type registration\n",
    '\n'.join(decls) + "\n\n// This is needed by an unavoidable GTK macros for type registration\n")
rep("CHECK_TYPE(GTKNoCSDAdwMessageDialog, GTKNoCSDADWMessageDialog)\n",
    "CHECK_TYPE(GTKNoCSDAdwMessageDialog, GTKNoCSDADWMessageDialog)\nCHECK_TYPE(GTKNoCSDGtkMenuButton, GTKNoCSDGTKMenuButton)\nCHECK_TYPE(GTKNoCSDGtkPopoverMenu, GTKNoCSDGTKPopoverMenu)\nCHECK_TYPE(GTKNoCSDGtkPopoverMenuBar, GTKNoCSDGTKPopoverMenuBar)\n")
if 'A' in P:
    rep("\t\t\tLOAD_SYMBOL(Library, gtk_spinner_get_type);\n",
        "\t\t\tLOAD_SYMBOL(Library, gtk_spinner_get_type);\n\t\t\tLOAD_SYMBOL(Library, gtk_widget_action_set_enabled);\n")
    m = re.search(r"(\t\t\tGET_SYMBOL\(gtk_im_context_set_cursor_location\);[ \t]*\\\n)", s)
    line = m.group(1)
    s = s.replace(line, line + "\t\t\tGET_SYMBOL(gtk_widget_action_set_enabled);\t\t\t   \\\n"
                  "\t\t\tGET_SYMBOL(gtk_widget_insert_action_group);\t\t\t   \\\n", 1)
if 'B' in P:
    rep("\tGTKNoCSDGetHdyTypes();\n\tGTKNoCSDGotTypes = true;\n}",
        "\tGTKNoCSDGetHdyTypes();\n\tGTKNoCSDGotTypes = true;\n\n\t// Hook GTK4 windows for the global menu, now that the types are known\n\tGTKNoCSDMenuHook();\n}")
    rep("void GTKNoCSDGetReferences(bool GetTypes) {",
        "void GTKNoCSDMenuHook(void);\nvoid GTKNoCSDGetReferences(bool GetTypes) {")
rep("// Macros for simplifying getting the correct function\n",
    pick(section) + "// Macros for simplifying getting the correct function\n")
# the base trigger: gtk_window_present, before the window is shown
rep("""void gtk_window_present(GtkWindow *Window) {
	// Entry point used by certain apps to display the window.
	// Hook it, execute our own function then the original

	GTKNoCSDGetReferences(true);
""", """void GTKNoCSDMenuAttach(GtkWindow *Window);
void gtk_window_present(GtkWindow *Window) {
	// Entry point used by certain apps to display the window.
	// Hook it, execute our own function then the original

	GTKNoCSDGetReferences(true);

	// The global menu has to be set before the window is realized
	GTKNoCSDMenuAttach(Window);
""")
open(out_c, 'w').write(s)

r = open(main_readme).read()
o = "- `GTK_NOCSD_NO_GTK4`: Setting to 1 disables the library for GTK4.\n"
assert r.count(o) == 1
bullet = ("- `GTK_NOCSD_GLOBAL_MENU`: Setting to 1 exports the header bar menu of GTK4 "
          "applications as their menubar, for a global menu")
bullet += (", while the desktop shows menubars itself (`gtk-shell-shows-menubar`).\n"
           if 'C' in P else ".\n")
r = r.replace(o, o + bullet)
open(out_readme, 'w').write(r)
