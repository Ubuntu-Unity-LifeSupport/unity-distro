# Layer B: what a GTK4 global menu actually needs

Measured on target, Ubuntu Unity 26.04, GTK4 4.22.4, 2026-09-23. Everything
here is an experiment, not a reading of documentation.

## The handoff's assumption was wrong in both directions

§3 of the handoff describes Layer B as "one patch exporting popover menu models
from GTK4, which gives the global menu and the HUD to every libadwaita
application at once". Two things are off.

**Worse than assumed: there is no way to deliver such a patch to applications.**
GTK4 has no module loading mechanism at all. Checked directly in the shipped
libraries:

| Symbol / string | libgtk-3.so.0 | libgtk-4.so.1 |
|---|---|---|
| `GTK_MODULES` | present | absent |
| `gtk_module_init` | present | absent |
| `gtk-modules` | present | absent |

`appmenu-gtk-module` works by being loaded into every GTK3 process through
`GTK_MODULES` and overwriting `realize` in the `GtkWindow`, `GtkApplicationWindow`
and `GtkMenuBar` class vtables. None of that is available under GTK4. Patching
`appmenu-gtk-module` for GTK4, which is what the handoff implies, cannot work -
it builds only `src/gtk-2.0` and `src/gtk-3.0`, and there is nothing to build a
`gtk-4.0` against.

**Better than assumed: the export machinery is intact and Unity already
supports it.** Stock, unpatched GTK4 still exports a menubar over
`org.gtk.Menus` and advertises it through X11 window properties. `mbtest.c` is
a twenty-line GTK4 application whose only unusual act is calling
`gtk_application_set_menubar()`. Its window carries:

```
_GTK_MENUBAR_OBJECT_PATH     = "/org/unitydistro/mbtest/menus/menubar"
_GTK_APPLICATION_OBJECT_PATH = "/org/unitydistro/mbtest"
_GTK_UNIQUE_BUS_NAME         = ":1.104"
```

and the model is readable on the bus:

```
$ gdbus call --session --dest :1.104 \
    --object-path /org/unitydistro/mbtest/menus/menubar \
    --method org.gtk.Menus.Start "[0]"
([(0, 0, [{'label': <'TestFile'>, ':submenu': <(1, 0)>},
          {'label': <'TestHelp'>, ':submenu': <(2, 0)>}])],)
```

**The Unity panel displays it.** Screenshot:
`../../screenshots/2026-09-23-gtk4-menu-in-unity-panel.png`. Hovering the panel
shows `TestFile  TestHelp`. No patched package was involved.

So the transport works end to end today. What is missing is only that real
applications never call `set_menubar`: they hang their menu on a
`GtkMenuButton` inside an `AdwHeaderBar`.

## The constraint that shapes any fix

`latetest.c` is the same application, except the menubar is attached six
seconds after the window is presented. Result: `_GTK_MENUBAR_OBJECT_PATH` is
never set, and the panel shows only the window title.

**The menubar has to be in place before the window is realized.** Anything
acting from outside the application has to get in before that moment, which
rules out the simplest approach of walking existing windows and attaching a
menu after the fact.

## What this makes the job

Not a GTK4 fork. Roughly:

1. Get into GTK4 processes before window realize. There is no module hook, so
   the remaining route is symbol interposition via `LD_PRELOAD`. There is a
   working precedent in this very session: `libgtk-nocsd.so.0` is already
   preloaded into the Unity session to suppress client-side decorations.
2. At that point find the window's header bar menu button and read its model.
   `gtk_menu_button_get_menu_model()` and `gtk_popover_menu_bar_get_menu_model()`
   are public API, so no private headers and no GTK internals are needed.
3. Hand it to `gtk_application_set_menubar()` before realize completes.

Open question for step 2: whether the application has populated the menu button
that early. If it has not, the shim needs to defer, and deferring is exactly
what `latetest.c` shows does not work - which would push the fix back into GTK4
itself.

## A GTK4 bug candidate, noted in passing

`gtk_application_set_menubar()` called after the window is realized silently
does nothing on X11: no property is set and no error is raised. Whether that is
intended is worth asking upstream. It is not our bug to fix and it does not
travel with any patch of ours.

## Reproducing

```bash
gcc mbtest.c   -o mbtest   $(pkg-config --cflags --libs gtk4)
gcc latetest.c -o latetest $(pkg-config --cflags --libs gtk4)
```

Run on target with `DISPLAY=:0` and the session's `DBUS_SESSION_BUS_ADDRESS`,
then `xprop -id $(xdotool search --name '^mbtest$')`.

---

# The shim works

`unity-gtk4-shim.c`, built and tested on target 2026-09-23. A GTK4 header bar
application's menu now appears in the Unity global menu, with no patch to GTK4,
to libadwaita, or to any package.

## Controlled comparison, file-roller

| | `_GTK_MENUBAR_OBJECT_PATH` on the window |
|---|---|
| without the shim | absent |
| with the shim | `/org/gnome/FileRoller/menus/menubar` |

The panel goes from showing only the window title to showing a menu entry that
opens file-roller's real menu - Создать архив…, Открыть…, Сохранить как…,
Боковая панель F9, Комбинации клавиш, Справка, О приложении. Insensitive items
are greyed, the radio item is marked and the accelerator is shown, so action
states survive the trip. Screenshots:
`2026-09-23-shim-before-after.png` and
`2026-09-23-gtk4-headerbar-menu-in-panel.png`.

## How it ended up working

Interposing `gtk_window_present`, `gtk_widget_set_visible` and
`gtk_widget_show` was the obvious approach and it failed. It fires for our own
test program, which calls `gtk_window_present` directly, and never fires for
file-roller: the call that shows its main window is made from inside GTK or
libadwaita, so it does not pass through a PLT we can interpose.

What works is the technique `appmenu-gtk-module` uses for GTK3 - take
`g_type_class_ref(GTK_TYPE_WINDOW)` and overwrite `realize` in the class
vtable. The only reason that module cannot do this under GTK4 is that it has no
way to get itself loaded, and `LD_PRELOAD` answers exactly that. Type
registration does not require `gtk_init()`, so the hook can be installed from a
library constructor.

## Breadth so far

| Application | Result |
|---|---|
| file-roller | menubar attached, renders, items work |
| simple-scan | menubar attached |
| yelp | shim ran, `no menu model found in this window` |
| transmission-gtk | did not start; result void |

Two of three that started. `yelp` is a real negative worth understanding rather
than papering over: the search looks only at the window's titlebar and its
direct child tree for a `GtkMenuButton` or `GtkPopoverMenuBar` carrying a
model. Applications that build the model lazily, or keep it somewhere else,
will be missed.

## What is not solved

- **The label is wrong.** The top-level entry is labelled with the application
  name, so the panel reads "File Roller  File Roller" - the window title and
  then the menu. A real design has to decide what a hamburger menu should be
  called once it is a menubar. Flattening its sections into several top-level
  menus is probably closer to what Unity expects, and is the obvious next
  experiment.
- **Breadth is barely measured.** Three applications is not a survey.
- **Nothing is known about side effects.** The hook is installed on every
  `GtkWindow`, dialogs and popups included. Nothing misbehaved in these runs,
  but nothing was checked either.
- **`GtkApplication` menubars are global to the application**, not per window.
  An application with two windows carrying different menus would get whichever
  realized first.
- **Delivery is unsolved.** For this to apply to every application, `LD_PRELOAD`
  has to be set session-wide, the way `libgtk-nocsd.so.0` already is.

---

# Promoting sections to top level: tried, and it does not work

The single top-level entry is labelled with the application name, so the panel
reads "File Roller  File Roller" - the window title, then a menu with the same
name. The obvious fix is to promote each section of the hamburger menu to its
own top-level menu, which is the shape Unity gets from a GTK3 application.

It fails for a reason that is not a matter of implementation.

## Hamburger sections carry no labels

Measured, not assumed. The shim now dumps the model it finds. simple-scan:

```
model has 2 top-level item(s)
  [0] section  label=(none)   section holds 3 item(s)
  [1] section  label=(none)   section holds 2 item(s)
```

file-roller is the same, four unlabelled sections, visible in the bus dump of
its exported menubar:

```
(1, 0, [{':section': <(1,1)>}, {':section': <(1,2)>},
        {':section': <(1,3)>}, {':section': <(1,4)>}])
```

A GTK3 menu bar is a list of *named* submenus - File, Edit, View. A hamburger
menu is a list of *unnamed* sections whose only job is to draw separators
between groups. The names a menu bar needs were never written down, because
nothing in the GTK4 design ever needed them.

## What the three modes actually produce

All three are in `unity-gtk4-shim.c`, selected by environment variable, so the
comparison can be repeated.

| Mode | Result |
|---|---|
| default, one wrapper | one top-level menu named after the application. Works; the name duplicates the window title |
| `UNITY_GTK4_SHIM_FLATTEN=1` | one top-level menu per section, each falling back to the application name because sections have none. simple-scan produced `simple-scan  simple-scan` |
| `UNITY_GTK4_SHIM_DIRECT=1` | GMenu promotes the section *items* to the top level: simple-scan showed `Одна страница  Все страницы из автоподатчика  Несколько страниц с планшетного сканера` as bare top-level actions. A row of buttons, not a menu bar |

Screenshots: `2026-09-23-shim-flatten-mode.png`,
`2026-09-23-shim-direct-mode.png`.

**The wrapper stays.** It is the only one of the three that produces something
shaped like a menu, and the problem it leaves - one redundant label - is far
smaller than the problems the other two create.

## So the real question is the label, not the structure

Options, none yet tested:

- a fixed word, localised the way Unity localises its own panel items. Honest,
  and it matches what the menu actually is.
- the application name only when it differs from the window title, which is the
  case that actually reads badly.
- ask the team: Unity has conventions here and we do not.

## Two corrections to earlier notes in this file

**simple-scan's crash is not ours.** It aborts with SIGABRT about ten seconds
after starting, and the control run without `LD_PRELOAD` at all does exactly the
same. Pre-existing, unrelated to this work, and the reason measurements taken on
that application were unstable.

**Environment variables do reach the application.** The shim now prints what it
sees, and `UNITY_GTK4_SHIM_FLATTEN` and `UNITY_GTK4_SHIM_LOG` both arrive. What
made the mode comparison on file-roller unreliable is different: its constructor
runs three times under one PID, so file-roller re-executes itself during
startup, and under repeated kill-and-restart it sometimes exits before showing a
window at all. Use it for single runs, not for A/B loops.

## Logging

`UNITY_GTK4_SHIM_LOG=/path` writes to a file with the pid on every line.
stderr is useless here: the window is frequently created in a process that
inherits the environment but not the caller's redirected stderr, so the
interesting output disappears.

---

# Widening the search, and checking what the hook disturbs

Work done while a web search for prior art is outstanding - neither of these
depends on its answer.

## Why yelp found nothing: the model is behind the popover

The shim now dumps the widget tree on a miss. yelp has **four**
`GtkMenuButton`s and every one reports `model=no`:

```
  tree   GtkMenuButton   <-- menu-ish
  tree        model=no popover=GtkPopover
  tree   GtkMenuButton   <-- menu-ish
  tree        model=no popover=GtkPopoverMenu
```

An application may call `gtk_menu_button_set_popover()` instead of
`set_menu_model()`, and then `gtk_menu_button_get_menu_model()` returns NULL
even though a menu exists. Where the popover is a `GtkPopoverMenu`, the model
is still reachable through `gtk_popover_menu_get_menu_model()`. The shim now
tries that as a fallback.

Two further things the tree showed, worth remembering:

- **yelp's header bar is not the window's titlebar.** It sits in the content
  tree under `AdwToolbarView` -> `GtkRevealer` -> `GtkWindowHandle` -> `GtkBox`
  -> `AdwHeaderBar`. Searching only `gtk_window_get_titlebar()` would miss it
  entirely; the shim walks the content tree too.
- **Several menu buttons per window is normal.** yelp has four. Taking the
  first one with a model is arbitrary, and which one is the *primary* menu is
  an open question.

`popovertest.c` reproduces the yelp pattern deterministically: a menu button
given a `GtkPopoverMenu` through `set_popover`. The fallback finds it -
`found GtkPopoverMenu behind a menu button at depth 4` - and the window gets
`_GTK_MENUBAR_OBJECT_PATH`. yelp itself turned out to be useless as a live test
subject: it exits within seconds when launched with no document, with or
without the shim.

## The hook fires on dialogs and does not disturb them

`realize` is hooked on every `GtkWindow`, and a dialog is one.
`dialogtest.c` opens a main window with a menu and then puts a `GtkAlertDialog`
and an about dialog on top.

```
realize (GtkApplicationWindow)
found GtkMenuButton with a model at depth 4
menubar attached, labelled "dialogtest"
realize (GtkWindow)
application already has a menubar, leaving it alone
realize (GtkWindow)
realize (GtkWindow)
```

The dialogs render, the process stays up, and stderr carries no GTK warnings,
criticals or assertions. The guard that skips an application which already has
a menubar is what keeps a dialog from overwriting the main window's menu -
which matters, because a `GtkApplication` menubar is application-wide.

## Test subjects, ranked by how much they can be trusted

| | |
|---|---|
| our own test programs | deterministic, use these |
| file-roller | shows a real menu, but re-executes itself at startup and under repeated restart often exits before showing a window. Single runs only |
| simple-scan | aborts with SIGABRT about ten seconds in, with or without the shim |
| yelp | exits at once without a document argument |

Measuring a shim against applications that fall over on their own wastes more
time than writing a test program that does not.

---

# How gtk-nocsd is packaged, and what we take from it

`apt source gtk-nocsd`. Upstream is
https://codeberg.org/MorsMortium/GTK-NoCSD, packaging by the Debian UBports
team with Jeremy Bícha as uploader. 3006 lines of C, no patches in `debian/`.
Everything below was verified against the running system on target.

## Delivery is one file

```
# /usr/lib/environment.d/50-gtk-nocsd.conf
LD_PRELOAD=libgtk-nocsd.so.0${LD_PRELOAD:+:$LD_PRELOAD}
```

Installed by `libgtk-nocsd0.install` into `usr/lib/environment.d`. systemd
reads that directory when building the user session environment, so the
variable reaches every process the user starts.

The `${LD_PRELOAD:+:$LD_PRELOAD}` idiom appends rather than overwrites, so
several such libraries compose. Ours would ship
`60-unity-gtk4-menu.conf` beside it and load after.

**Opt-out is by shadowing, not by a setting.** The package description tells
users to create an *empty* file with the same name in a higher-priority
directory - `/etc/environment.d/50-gtk-nocsd.conf` for the machine or
`~/.config/environment.d/50-gtk-nocsd.conf` for one user. That is how
`environment.d` precedence works, and it costs no code.

## The setuid trick, which we would not have guessed

`debian/rules`:

```
execute_after_dh_fixperms:
	chmod 4644 debian/*/usr/lib/*/libgtk-nocsd.so.0
```

Mode 4644 - setuid, not executable. On target: `-rwSr--r-- root root`. The
reason is in `debian/libgtk-nocsd0.lintian-overrides`: a globally preloaded
library makes the dynamic linker print a warning on every invocation of a
privileged program, `ping` among them. Marking the library setuid makes ld.so
preload it without the warning. The override cites `sdate` as precedent.

Any session-wide `LD_PRELOAD` of ours hits the same thing.

## Disabling itself where it does not belong

The constructor checks `XDG_CURRENT_DESKTOP` and bows out on anything GNOME
except Flashback. It also skips AppImages that carry no GTK of their own, and
Cambalache's `merengue`.

When it decides it is not wanted it does not merely return - it **blanks
`LD_PRELOAD` in `environ` and `execve`s the program again**, so the library is
gone from that process and from everything it spawns.

That is worth knowing for a second reason. A preload library that re-execs
makes a constructor appear to run several times under one pid - the pattern we
saw with file-roller and attributed to the application. It may well have been
this.

Our shim now gates on `XDG_CURRENT_DESKTOP` containing `Unity` - the session on
target reports `Unity:Unity7:ubuntu`. Verified: the menubar is attached under
Unity and the shim does nothing under `GNOME` or `KDE`.
`UNITY_GTK4_SHIM_FORCE=1` overrides for testing. We return early rather than
re-exec; re-execing inside somebody else's process is a heavy thing to do and
early return costs nothing.

## Build details worth copying

- `Build-Depends: libadwaita-1-dev` - that is how the adwaita types are reached
- `DEB_LDFLAGS_MAINT_APPEND = -Wl,-z,defs` - no undefined symbols at link time
- `DPKG_GENSYMBOLS_CHECK_LEVEL = 4` with a full `.symbols` file, although there
  is no `-dev` package and lintian is told so
- `Provides: gtk-nocsd`, with `gtk3-nocsd` and `libgtk3-nocsd0` kept as
  transitional packages in `Section: oldlibs`

## What this leaves open for us

Delivery, opt-out, permissions and desktop gating are answered. What is not:
the top-level label, which menu button to take when a window has several, and
whether reading the widget tree through nocsd's interposed
`gtk_widget_get_first_child` ever shows us something different from the real
one.

---

# Does nocsd show us a different widget tree?

It does, and the difference does not touch us.

## What nocsd does to the tree

It restructures the window - inserting a vertical box and moving the header
bar into it - and then lies about the result so applications do not notice.
`gtk_window_get_child`, `gtk_widget_get_first_child`, `gtk_widget_get_last_child`
and `gtk_window_get_titlebar` are all interposed and pass their answer through
an internal `GTKNoCSDGTK4Content()` that hides nocsd's own scaffolding.

Our menu search walks exactly those calls, so the question was whether it sees
the real tree or a doctored one.

## Measured

`popovertest.c`, tree dumped from inside the realize hook, twice: shim alone,
and nocsd loaded before the shim.

```
$ diff t-alone.tree t-nocsd.tree
7,12d6
<   tree           GtkButton
<   tree             GtkImage
<   tree           GtkButton
<   tree             GtkImage
<   tree           GtkButton
<   tree             GtkImage
```

Six lines, and that is the whole difference: the three buttons inside
`GtkWindowControls` - minimise, maximise, close - which nocsd removes because
the window manager is drawing them instead. `GtkWindowControls` itself stays,
empty.

| | shim alone | nocsd + shim |
|---|---|---|
| plain `GtkButton` in the tree | 3 | 0 |
| `GtkMenuButton` | 1 | 1 |
| result | `found GtkPopoverMenu behind a menu button at depth 4` | identical, same depth |

The menu button, its `GtkPopoverMenu` and the model are present and at the same
depth either way, and the menubar is attached in both.

## Two things this settles

**The search is safe under nocsd.** It removes decoration widgets, not menu
widgets.

**Being lied to is in our favour here.** nocsd hides its own inserted box, so
what we walk is the tree the application built rather than the one nocsd
rearranged. Had it exposed its scaffolding, our depth-first search could have
wandered into it.

Worth re-checking if either side changes: this is a behavioural dependency on
another package's internals, and nothing guarantees it.

---

# The label was never ours to choose

Rule 0 answered this one without leaving the machine. `apt-get source
indicator-appmenu` - the component that draws the global menu.

`src/window-menu-model.c` reads **five** window properties, not the one we knew
about:

```
_GTK_UNIQUE_BUS_NAME
_GTK_APP_MENU_OBJECT_PATH
_GTK_MENUBAR_OBJECT_PATH
_GTK_APPLICATION_OBJECT_PATH
_GTK_WINDOW_OBJECT_PATH
_UNITY_OBJECT_PATH
```

and carries a dedicated `add_application_menu()`:

```c
if (appname != NULL) {
    menu->priv->application_menu.label = GTK_LABEL(gtk_label_new(appname));
} else {
    menu->priv->application_menu.label =
        GTK_LABEL(gtk_label_new(_("Unknown Application Name")));
}
```

Unity has a first-class notion of an **application menu**, separate from the
menu bar, and it labels that entry itself - from the application name, falling
back to "Unknown Application Name". The convention exists and is built into
indicator-appmenu. There was never a label for us to invent.

`_GTK_APP_MENU_OBJECT_PATH` is the old GNOME application menu, set through
`gtk_application_set_app_menu()`. GTK4 removed that API, so no GTK4 application
ever sets the property - but Unity's consumer still honours it.

## Taking that route, and it works

`UNITY_GTK4_SHIM_APPMENU=1` exports the model with
`g_dbus_connection_export_menu_model()` and sets the property itself with
`XChangeProperty`, since GTK4 offers no API for it. This has to happen *after*
realize: before it there is no surface and no X11 window, so the hook chains to
the real realize first.

| Application | Property | Panel shows |
|---|---|---|
| `popovertest` (no .desktop file) | `/org/unitydistro/popovertest/unityshim/appmenu` | **Unknown Application Name** - Unity's own fallback |
| `file-roller` | `/org/gnome/FileRoller/unityshim/appmenu` | **File Roller** |

The menu opens and renders file-roller's real items, greying and accelerators
intact: `2026-09-23-app-menu-route.png`. `_GTK_MENUBAR_OBJECT_PATH` is not set
in this mode, so this is the app-menu path on its own.

Seeing "Unknown Application Name" appear unprompted is the confirmation that
matters: the label is coming from Unity's code, not ours.

## What it does not fix

The panel still reads `File Roller  File Roller` - window title, then
application menu. The application-menu entry sits beside the title rather than
replacing it, so the redundancy is the same as with the wrapper.

That is worth stating plainly: **the duplication is a property of Unity's panel
layout, not of our labelling.** We cannot remove it from the application side,
and we should not try. Whether it is a problem at all is a question for the
team - a GTK3 application shows its title and then File, Edit, View, so a title
followed by one menu named after the application may be exactly what they
expect.

## Which of the two routes to keep

Both work. The app-menu route is better on the merits:

- the label is Unity's, by Unity's convention, including a fallback we did not
  have to design
- it occupies the slot meant for precisely this, rather than presenting a
  hamburger as if it were a menu bar
- it leaves `gtk_application_set_menubar()` alone, so an application that has a
  real menu bar keeps it

Against it: it depends on `_GTK_APP_MENU_OBJECT_PATH`, which GNOME deprecated
around 2019 and removed from GTK4. Unity still reads it, but building on a path
its own upstream abandoned deserves a question to the team before it becomes
the design.

Both are kept behind environment variables until that is answered.

## Known rough edge

The second realize on the same window tries to export the model again and gets
`Object already exported for interface org.gtk.Menus`. Harmless - the first
export stands and the property is already set - but it needs a guard.

---

# What the panel actually shows, measured

The host session's reading of the code was right about where the label comes
from and wrong about the layout, so both halves are recorded here with the
experiments that settle them.

## Right: the label comes from the .desktop file

`window-menu-model.c` lines 479-500 take `bamf_application_get_desktop_file()`,
build a `GDesktopAppInfo` from it and use `g_app_info_get_name()`. The menu
model is not consulted for the name at all. That is why unlabelled hamburger
sections never mattered: **set `_GTK_APP_MENU_OBJECT_PATH` and the name arrives
from the system, localised, identical to every other application.**

Confirmed from the other end: `popovertest`, which has no `.desktop` file,
shows Unity's own `Unknown Application Name`.

## Right: both entries are shown, application menu first

Lines 479 and 501 are two independent `if`s, not `if/else`. An application that
sets both properties gets both entries. For a libadwaita application with no
real menu bar, set **only** `_GTK_APP_MENU_OBJECT_PATH`, or the same hamburger
items appear twice by two different routes.

## Wrong: the title is not replaced on hover

The claim was that the window title and the menus are two states of one area
and never visible together. Measured with `mbtest`, which exports a real menu
bar:

| cursor | panel |
|---|---|
| away from the panel | `mbtest` |
| over the panel | `mbtest    TestFile  TestHelp` |

The left item stays and the menus appear beside it.
`2026-09-23-panel-hover-states.png`.

Settings are the stock ones: `com.canonical.Unity always-show-menus false`,
`integrated-menus false`.

## And the left item is the application name, not the title

Two experiments that look contradictory until put together.

- Renaming `mbtest`'s window with `xdotool set_window --name` changed the panel
  text. So it followed the title.
- `file-roller` opened on `sample.zip` has the window title `sample.zip`, and
  the panel shows `File Roller`.

The difference is the `.desktop` file. `file-roller` has one and BAMF matches
it, so the panel shows the application name; `mbtest` has none, so it falls
back to the window title.

**The panel's left item and the application menu entry are fed from the same
source** - the `Name=` field of the `.desktop` file. Labelling the entry the way
Unity labels it therefore guarantees it matches the item already beside it.

## So the duplication is structural, and it is a question for the team

`File Roller  File Roller` is not a consequence of our wrapper, and the
application-menu route does not remove it: Unity names the entry from the same
`.desktop` field it uses for the panel item. Neither route avoids it, because
the name is correct in both places.

What we cannot tell from here is whether this is a problem at all. Applications
that had app menus in the GNOME 3.10-3.30 era presumably looked exactly like
this under Unity, and the mechanism was built for them. That makes it a
question about intent rather than about code, and it belongs in the first
conversation with the team along with the other one:

- is `_GTK_APP_MENU_OBJECT_PATH` a path you still consider alive, given GNOME
  deprecated app menus in 3.32 and GTK4 removed the API
- is an application-menu entry named the same as the panel item beside it the
  intended appearance, or something that used to be avoided

Both are architecture questions. Answering them after the package is written
would be the expensive order.

---

# The HUD picks it up too

Grepping the installed system for `_GTK_APP_MENU_OBJECT_PATH` turned up four
readers and no writers:

| Binary | Package |
|---|---|
| `libgtk-3.so.0` | libgtk-3-0t64 |
| `libgtk-4.so.1` | libgtk-4-1 |
| `libmuffin.so.0` | libmuffin0t64 (Cinnamon) |
| `hud-service` | **hud** |
| `libappmenu.so` | vala-panel-appmenu |

plus `indicator-appmenu`. Meanwhile GTK3 exports
`gtk_application_set_app_menu`, `get_app_menu` and `prefers_app_menu`, and
GTK4 exports **none** - the property name survives in the binary, the API does
not. So the channel is empty because the producing side left the toolkit, not
because it is broken.

`hud-service` in that list was unexpected. The HUD is one of Unity's signature
features - search a window's menus from the keyboard - and it reads the same
property.

## Measured

`popovertest` with `UNITY_GTK4_SHIM_APPMENU=1`, plus a `.desktop` file so BAMF
can match the window. Alt to open the HUD, typed `Popover`:

```
Popover Item One
Popover Item Two
```

Those are exactly the two items of the application's hamburger popover.
`2026-09-23-hud-finds-hamburger-items.png`.

**So publishing a GTK4 hamburger menu as an application menu does not only put
it in the panel - it makes its items keyboard-searchable in the HUD.** For an
application that previously offered the HUD nothing at all, that is the larger
half of the result.

## And the label theory closes cleanly

The same run confirms where the name comes from, from both ends:

| `popovertest` | panel shows |
|---|---|
| no `.desktop` file | `Unknown Application Name` |
| `.desktop` with `Name=Popover Test` | `Popover Test` |

Nothing about the application changed between the two except a file in
`/usr/share/applications`. The label is the `.desktop` `Name=` field reached
through BAMF, exactly as `window-menu-model.c` says.

It also shows the duplication in a controlled case: the panel reads
`Popover Test  Popover Test` - the BAMF name beside the application menu entry
Unity labelled from the same field.

## Which strengthens the case for asking rather than choosing

The application-menu route now has a second argument behind it that the menubar
route does not: HUD coverage. It also still rests on a property GNOME
deprecated and GTK4 dropped. Both belong in the same question to the team, and
the HUD result makes it worth asking well.

---

# Choosing between the two routes: menubar wins

Three findings settle it, and the deciding one contradicts what we expected.

## The reference implementation never uses app menu

`appmenu-gtk-module` - the module Ubuntu builds into the package installed on
target - sets exactly three properties on X11, verified in `src/platform.c`:

```c
_GTK_UNIQUE_BUS_NAME
_UNITY_OBJECT_PATH
_GTK_MENUBAR_OBJECT_PATH
```

and on Wayland it passes the app menu slot explicitly as nothing:

```c
const char *app_menu_path = NULL;
gdk_wayland_window_set_dbus_properties_libgtk_only(..., app_menu_path, ...)
```

No comment explains the choice, but the choice is deliberate. Everything a GTK3
application has becomes a menubar. Sending GTK4 applications down the app-menu
channel instead would put two different shapes in one panel.

## The HUD is not an argument for app menu after all

The app-menu route makes HUD find the hamburger items, which looked like its
decisive advantage. Tested the same application through the menubar route:

```
Popover Item One   (popovertest)
Popover Item Two   (popovertest)
```

The HUD finds them either way - and through the menubar route it also shows
which menu each item belongs to, which the app-menu route does not.
`2026-09-23-hud-via-menubar-route.png`.

So HUD coverage comes from exporting the model at all, not from the channel.
The advantage we thought was unique is not.

## Ubuntu used to patch app menus away

Ubuntu 14.04 shipped patches restoring full menu bars to GNOME applications
that had moved to app menus - Nautilus, Rhythmbox, File Roller, Calculator.
The reasoning recorded at the time was that a single app-menu entry works in
GNOME and works badly on desktops that kept traditional menus.

So `File Roller  File Roller` is not an intended appearance we failed to
understand. It is a state Ubuntu spent effort avoiding, one application at a
time.

## Decision

**The menubar route.** Consistent with the reference implementation, covered by
the HUD with better context, and not resting on a channel whose producing side
left the toolkit. Both remain in the shim behind environment variables, because
a measurement someone can repeat is worth more than a decision recorded in
prose.

What we give up is the automatic label. Through the menubar route the top-level
name comes from `g_get_application_name()`, which for `popovertest` yields
`popovertest` rather than the `.desktop` name `Popover Test`. That happens to
avoid the duplication, but by accident rather than design.

## The label is now a small question with a precedent

It stops being an architecture question and becomes a UI one, and the answer
does not have to be a single opinion. Cinnamon's Global Application Menu applet
offers *show or hide the application name* as a setting, and vala-panel-appmenu
carries the same discussion. Making it configurable is the established way this
particular taste question gets handled.

## Still missing from our shim

`appmenu-gtk-module` also sets `_UNITY_OBJECT_PATH`, which we do not - GTK4 sets
only the paths it knows about. The HUD worked without it, so it is not
load-bearing here, but it is a difference from the reference worth
understanding before any of this is packaged.

---

# The label is a setting

A hamburger menu has no name of its own, so the entry we create needs one, and
there is no right answer. Named after the application it repeats what the panel
already shows beside it; named neutrally it says less. The desktops that ship a
global menu do not settle this either - Cinnamon's Global Application Menu
applet offers *show or hide the application name*, and vala-panel-appmenu
carries the same discussion - so it is a setting here too rather than an
opinion baked into the code.

## GSettings, not an environment variable

`com.ubuntu-unity.gtk4-menu.gschema.xml` in this directory, key
`show-application-name`, boolean, default true. Installed and tested on target.
A preference a user can change belongs in GSettings; an environment variable
would mean editing `environment.d` and logging out.

`UNITY_GTK4_SHIM_LABEL=app|generic` overrides it for testing and is what runs
when the schema is not installed, so the shim still works uninstalled.

## Measured, with the setting flipped under a live panel

| `show-application-name` | panel |
|---|---|
| `true` | `Popover Test  Popover Test` |
| `false` | `Popover Test  Menu` |

`2026-09-23-label-setting.png`. Nothing changed between the two runs except the
GSettings key.

## Where the name comes from when the setting is on

`g_desktop_app_info_new(<application-id>.desktop)`, then
`g_app_info_get_name()`. That is the same `Name=` field Unity's panel reads
through BAMF, so turning the setting on genuinely repeats what is beside it
rather than something approximately like it.

**This only works when the .desktop file is named after the application id**,
which is the current convention. Our own test file was first installed as
`unityshim-popovertest.desktop` and the lookup missed, falling back to
`g_get_application_name()` - which produced `popovertest` rather than
`Popover Test`. Renaming it to `org.unitydistro.popovertest.desktop` fixed it.

Worth keeping: applications that do not follow the convention get the fallback,
and the fallback is whatever the application passed to
`g_set_application_name()`, or its program name. That is not wrong, just
quieter and less predictable.

## The neutral label needs translating

`_("Menu")` is marked for translation and nothing translates it yet - the shim
has no gettext domain. Fine for a prototype, not for a package.

---

# Packaged, installed, and it broke the session

The package builds, installs from our own repository and delivers itself
correctly. Then it takes the desktop down, and the reason is a design mistake
that only a session-wide install could expose.

## What worked

`unity-gtk4-menu` 0.1, built in a clean resolute chroot, published to the local
archive, installed on target with `apt`:

- library at `/usr/lib/x86_64-linux-gnu/libunity-gtk4-menu.so.0`, mode
  `-rwSr--r--` as intended
- `environment.d` snippet installed, and after a reboot the session had
  `LD_PRELOAD=libunity-gtk4-menu.so.0:libgtk-nocsd.so.0` - both libraries
  composed through the `${LD_PRELOAD:+:$LD_PRELOAD}` idiom, exactly as designed
- GSettings schema installed, trigger recompiled the schema cache, key readable

## What broke

After the reboot: `unity-panel-service` not running, and fresh crash files for
`compiz`, `unity-settings-daemon`, `onboard`, `apport-gtk`,
`a11y-profile-manager-indicator`, `livepatch-notification` and
`ubuntu-advantage-notification`.

## Why

| | our library | gtk-nocsd |
|---|---|---|
| GTK libraries in `NEEDED` | `libgtk-4.so.1` | **none** |

Confirmed directly:

```
$ LD_PRELOAD=libunity-gtk4-menu.so.0 onboard --help
Gdk-ERROR: gdk_display_manager_get() was called before gtk_init()
```

A preloaded library is loaded into **every process on the machine**, not only
into the GTK4 applications it was written for. Ours links `libgtk-4.so.1`, so
it drags GTK4 into every one of them, and its constructor calls
`g_type_class_ref(GTK_TYPE_WINDOW)` unconditionally. In a GTK3 process that is
fatal; in a non-GTK process it is pointless.

`gtk-nocsd` links no GTK at all. Its 3006 lines of `dlsym` calls against
explicit library handles, which looked like ceremony when we first read them,
are the whole answer to this problem.

## The fix, and why the flaw survived so long

Resolve every GTK symbol with `dlsym` at runtime rather than linking, and do
nothing unless GTK4 is already loaded in the process - `dlopen("libgtk-4.so.1",
RTLD_NOLOAD)` returning non-NULL is the test.

Nothing in the prototype could have caught this. Every measurement so far set
`LD_PRELOAD` on one command at a time, so the library only ever entered
processes that were already GTK4 applications. The bug needs the library to be
loaded where it does not belong, which is precisely what packaging it does.

## State

Package removed from target, which recovered fully after a reboot - compiz and
`unity-panel-service` running, `LD_PRELOAD` back to `libgtk-nocsd.so.0` alone.
The binary is pulled from the local archive so nobody installs it. Source stays
at https://github.com/Ubuntu-Unity-LifeSupport/unity-gtk4-menu with this
recorded, because the packaging itself is right and only the symbol handling is
wrong.

---

# Rewritten on dlsym, and the session survives

`unity-gtk4-menu` 0.2. The change is in how the library reaches GTK, not in
what it does.

Nothing is linked but libc:

```
$ readelf -d libunity-gtk4-menu.so.0 | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so.6]
```

Every GTK and GLib symbol is resolved with `dlsym`, and the constructor first
asks `dlopen("libgtk-4.so.1", RTLD_NOLOAD)` - which returns a handle only if
the library is already mapped here. In anything that is not a GTK4 application,
that is NULL and the library stops without having touched GTK.

Headers are still included, for types and struct layouts. `GTK_IS_*` and
`GTK_TYPE_*` are avoided throughout: they expand into calls, and a call is what
puts a library back into `NEEDED`. Guessing the offset of `realize` in
`GtkWidgetClass` instead of taking it from the header would have been worse.

## Verified, in the order the failures happened

| | before | after |
|---|---|---|
| `onboard --help` with the library preloaded | `Gdk-ERROR: gdk_display_manager_get() was called before gtk_init()` | exits cleanly, no errors |
| a non-GTK process | GTK4 dragged in | `GTK4 is not loaded in this process, doing nothing` |
| session after install and reboot | `unity-panel-service` dead, seven fresh crashes | compiz, `unity-panel-service` and eight indicators running, one crash and it is the documented `light-locker` |
| a GTK4 application | menu attached | menu attached |

Installed from our own archive, the session composes both preloads as intended:

```
LD_PRELOAD=libunity-gtk4-menu.so.0:libgtk-nocsd.so.0
```

and an application launched with that environment logs:

```
GTK4 is not loaded in this process, doing nothing
GTK4 is not loaded in this process, doing nothing
hooked GtkWindow::realize
hooked GtkApplicationWindow::realize
popover menu behind a button at depth 7
menubar attached, labelled "popovertest"
the application already has a menubar
```

The first two lines are the early `exec` stages before GTK4 is mapped. They
also settle an old puzzle: the constructor appearing to run several times under
one pid was never file-roller re-executing itself, it is simply what a preload
sees across an exec chain.

## A guard, not a comment

`make check` runs before `make install` and fails the build if any GTK or GLib
library reappears in `NEEDED`. The comment explaining why would not have caught
a future edit; the check will. This class of mistake is invisible until the
library is installed session-wide rather than preloaded onto one command, so
the build is the only place to catch it cheaply.

---

# Breadth on real applications, with the package installed

The first measurements with `unity-gtk4-menu` installed session-wide, on real
applications launched with the **whole** session environment copied from
compiz. An earlier harness exported only a few chosen variables, dropped
`LD_PRELOAD` and `XDG_DATA_DIRS`, and so tested itself rather than the package.

| Application | Result |
|---|---|
| file-roller | menu attached, labelled **File Roller** from its `.desktop` |
| yelp, given a document | **popover behind a button found**, labelled **Справка** |
| gcr-viewer | `no menu model` - it has no menu, correct negative |
| zenity | a dialog with no menu, nothing to attach |
| transmission-gtk | did not start; void |

Two things this settles. The yelp fallback - reaching the model through a
`GtkPopoverMenu` when `get_menu_model()` returns NULL - now works on the real
application rather than only on our imitation of it. And labels come from the
`.desktop` file, localised: the earlier fallbacks to the program name were the
harness missing `XDG_DATA_DIRS`, as suspected.

Along the way dozens of non-GTK processes - `xdotool`, `xprop`, `pgrep`,
`sleep` - got the preload, logged `GTK4 is not loaded in this process, doing
nothing`, and ran normally. No new crashes.

## Two rough edges yelp exposed

Its exported model, read off the bus:

```
(1, 3, [{'custom': <'zoom-controls'>}])
(1, 5, [{'action': <'win.yelp-show-about-dialog'>, 'label': <'О приложении'>}])
```

**A blank row.** `custom` marks a slot in a `GtkPopoverMenu` where the
application places a live widget - here, zoom controls. A widget cannot cross
D-Bus, so it arrived as an empty, nameless entry. Fixed in 0.3: the model is
copied before export with such items removed, along with any section the
removal leaves empty. yelp drops two entries and reads cleanly -
`2026-09-23-yelp-menu-cleaned.png`.

**"О приложении" is greyed out, and stays that way.** The action
`win.yelp-show-about-dialog` is not among the eleven actions the window
exports. yelp registers it in an action group attached to a widget with
`gtk_widget_insert_action_group()`, which is only reachable from inside that
widget's scope; the window's exported group never contains it, so Unity cannot
activate it and shows it insensitive.

Not fixed, and not simple to: it would mean finding widget-scoped action
groups and exporting them under names the menu model's `win.` prefix resolves
to. A known limitation for now. _(Wrong about the mechanism - it is a class action - and fixed in 0.4; see "Class actions" below.)_ It also means "items work if they are shown as
active" is a claim to check per application, not assume.

---

# Class actions: "About Help" works from the global menu (0.4)

_Agent B, 2026-09-24, on `target2`._

## Correction: yelp does not use `gtk_widget_insert_action_group()`

The section above says yelp registers `win.yelp-show-about-dialog` in an action
group inserted on a sub-widget. It does not. yelp 49 installs it on its window
class:

```
src/yelp-window.c:339:
    gtk_widget_class_install_action (widget_class, "win.yelp-show-about-dialog", ...
```

A **class action**, owned by `YelpWindow` (an `AdwApplicationWindow`). It is
still invisible over D-Bus for the same underlying reason: the window exports
its `GActionMap` as `/…/window/N`, and class actions live in the widget's
action muxer, not in that map. But the difference decides the fix. Class
actions can be enumerated through public API (`gtk_widget_class_query_action`,
GTK 4.0+); groups inserted on a widget cannot.

## Was it already solved? (rule 0)

- Installed system and archive (`target2`, clean): no GTK4 menu exporter other
  than ours; `appmenu-gtk3-module`, `unity-gtk3-module` cover GTK3 only.
- GTK 4.22.4 source: `gtk_widget_action_set_enabled` has no getter;
  `GtkActionMuxer` is private and not a `GActionGroup`; the muxer checks class
  actions before inserted groups at every level (`gtk_action_muxer_activate_action`).
- Web, through the host session (2026-09-23 23:05Z): no GTK issue or MR about
  exporting widget/class actions over D-Bus; vala-panel-appmenu has no GTK4
  discussion at all; KDE leaves GTK4 menus to the application. Nothing to reuse,
  and nobody found a wall either.

## The fix

When the header bar model is copied for export, each item's action is looked
up as a class action on the menu's owner widget (the `GtkMenuButton`, or the
`GtkPopoverMenuBar`) and its ancestors. If found and stateless, the exported
item is pointed at `win.unity-gtk4-menu-<name with dots as dashes>`, a
`GSimpleAction` added to the window's action map whose `activate` calls
`gtk_widget_activate_action_variant(owner, original_name, parameter)` - the
same resolution the application's own popover performs. The item's target is
kept, so parameterised actions work unchanged.

The menubar belongs to the application, but `win.` resolves against the
focused window, so every `GtkApplicationWindow` of the application gets its
own stand-ins pointing at its own menu button.

Not proxied, and logged by name with `UNITY_GTK4_MENU_DEBUG=1`:

| Kind | Why |
|---|---|
| property action (`install_property_action`) | carries state; a plain stand-in would show a toggle without its check mark |
| prefix other than `app.`/`win.` | usually a group inserted on a sub-widget; public API cannot enumerate those |

The stand-in is always enabled - there is no public getter for a class action's
enabled state. Activating one the application disabled does nothing, as it
would in the application.

## Verified

`tests/classtest.c` in the package: one item of each kind. With 0.4 preloaded,
the window exports `map-hello`, `unity-gtk4-menu-win-class-hello` and
`unity-gtk4-menu-win-class-param` (signature `s`); `class-toggle` and
`inner.hello` stay as they were. `gdbus call … org.gtk.Actions.Activate` on the
two stand-ins prints `ACTIVATED win.class-hello` and
`ACTIVATED win.class-param abc`.

yelp 49.0-5ubuntu0.1, GTK 4.22.4, on `target2`:

| | 0.3 | 0.4 |
|---|---|---|
| "О приложении" in the Unity panel menu (F10) | greyed out | active |
| activated from the panel | - | the About dialog opens |
| second window (`win.yelp-window-new`), activated over D-Bus | - | the dialog opens over the second window |
| "Предыдущая/Следующая страница" (exported, disabled) | greyed | still greyed - exported actions untouched |

Then the `sbuild` package, installed session-wide with `dpkg -i` and a reboot:
63 processes map the library, compiz carries the preload, no new crash reports;
yelp launched from its `.desktop` file shows "О приложении" active and opens the
dialog from the panel. file-roller: menu unchanged, no stand-ins needed, no
warnings.

Screenshots: `2026-09-24-yelp-menu-0.3-about-greyed.png`,
`2026-09-24-yelp-menu-0.4-about-active.png`,
`2026-09-24-yelp-about-from-global-menu.png`.

Not yet checked: the HUD route to the same item, and applications other than
yelp that use class actions in header bar menus - the debug log will name them
when the breadth run is repeated.

---

# Breadth with 0.4, and the HUD

_Agent B, 2026-09-24, on `target2`, 0.4 installed session-wide._

Seventeen GTK4 applications, each launched in the real session environment
with `UNITY_GTK4_MENU_DEBUG=1`, then read the way Unity reads them: the
`_GTK_*` window properties, the menubar over `org.gtk.Menus`, and every item's
action checked against the exported `app` and `win` groups (`DescribeAll`).
"Missing" below means an item whose action is not exported at all - Unity shows
it greyed and cannot activate it. Items the application disabled itself are
counted as correct.

| Application | Menu exported | Items | Proxied by 0.4 | Missing | Notes |
|---|---|---|---|---|---|
| yelp | main | 7 | 1 | 0 | |
| loupe | main | 9 | **6** | 0 | Open, Open With, Print, Set as Background, Delete, About - all class actions |
| kgx (Console) | main | 6 | **5** | 0 | |
| file-roller | main | 12 | 0 | 0 | |
| baobab | main | 6 | 0 | 0 | |
| gnome-clocks | main | 3 | 0 | 0 | |
| gnome-system-monitor | main | 5 | 0 | 0 | |
| papers | help/about only | 3 | 0 | 0 | not probed for `primary` - the probe run did not start |
| gnome-calculator | **wrong menu** (mode selector) | 6 | 0 | 0 | |
| gnome-logs | **wrong menu** (boot selector) | 5 | 0 | 0 | |
| simple-scan | **wrong menu** (scan type) | 5 | 0 | 0 | |
| gnome-text-editor | **wrong menu** (search options) | 3 | 0 | **3** | `search-options.*` |
| nautilus | **wrong menu** (current folder) | 17 | 0 | **17** | `view.*`, `slot.*` |
| gnome-font-viewer | none | - | - | - | no `GtkMenuButton` in the tree at realize |
| gnome-contacts | none | - | - | - | same |
| gnome-characters | none | - | - | - | gjs: **shim never hooked** |
| gnome-weather | none | - | - | - | gjs: **shim never hooked** |

transmission-gtk exited at start, with and without the shim, as in the first
breadth run.

## Finding 1: class actions were the right target

Where the right menu is found, 0.4 leaves **nothing** missing: 12 class actions
proxied across loupe, kgx and yelp, every other item already exported. Without
0.4 loupe would show six of nine items greyed and kgx five of six.

## Finding 2: the shim often takes the wrong menu

`find_menu_model` returns the first menu button in tree order. Five of the thirteen
applications where a menu was found have a secondary menu button earlier in the tree. A probe build
logged every `GtkMenuButton` with `gtk_menu_button_get_primary()` (GTK 4.4+,
the button F10 opens; libadwaita applications set it on the main menu per the
HIG):

| Application | Buttons with a model | `primary` set on | Taken today |
|---|---|---|---|
| gnome-calculator | 2 | main menu (`app.new-window`) | mode selector |
| gnome-logs | 2 | main menu (`app.new-window`) | boot selector |
| simple-scan | 2 | main menu (`app.email`) | scan type |
| gnome-text-editor | 2 | none | search options |
| nautilus | 5 | none | current folder menu |
| yelp, loupe, kgx, file-roller, baobab, clocks, system-monitor | 1-2 | main menu | main menu |

So: take the `primary` button when there is one - that fixes three
applications outright. In the others the primary button carries the menu taken
today; kgx has two buttons carrying the same main menu and today
takes the non-primary one, with the same items. Where none is
marked, the main menu is the one made of `app.`/`win.` actions (text-editor
`app.new-window`, nautilus `app.clone-window`), while the wrong candidates are
built from sub-widget groups (`search-options.`, `view.`). Preferring the
candidate with the most `app.`/`win.` items would pick correctly in both.
Not implemented yet.

This also changes the weight of the inserted-group case: nautilus's 17 missing
items are the *wrong* menu. Its main menu is `app.*`.

## Finding 3: gjs and Python applications are not reached at all

The shim checks for GTK4 in its constructor, with `RTLD_NOLOAD`. A gjs or
PyGObject application loads GTK4 later, through GObject Introspection, so the
check fails and the shim does nothing: gnome-characters and gnome-weather log
`GTK4 is not loaded in this process`. Interposing a GTK symbol would not help
either - GI resolves symbols with `dlsym` on libgtk's own handle, whose scope
does not include preloaded libraries. Needs a different trigger; not
investigated further.

## Finding 4: menus built after realize

gnome-font-viewer and gnome-contacts have no `GtkMenuButton` in the widget tree
when the window is realized - their header bars are filled in later
(navigation pages). The shim looks once, at realize, and finds nothing.

## HUD

yelp, 0.4 installed: Alt, typing "приложении" lists **"О приложении (Справка)"**,
and Enter opens the About dialog. Before Enter the dialog is not on screen, so
the HUD's activation - not an earlier one - opened it.
`2026-09-24-hud-yelp-about.png`, `2026-09-24-hud-yelp-about-opened.png`.

Harness: `harness/audit.py` (reads one window as Unity does) and
`harness/breadth.sh` in this directory.
