# unity-gtk4-menu 0.14 design: follow the shown menu (-028), bound the stand-in pass (-030), Xsession snippet (-039)

Agent B, 2026-10-17. **Round 1**, for the Design Challenger. No code exists. The only code so far is a prototype of
the Xsession snippet in the scratchpad, sourced on target2 for part C's facts.

Tasks:
- UNITY-20261013-028: follow the shown menu. Measured in this card's `README.md`.
- UNITY-20261013-030: `add_stand_ins` walks every other window on every rebuild.
- UNITY-20260927-039: the menu is lost when the session has an LD_PRELOAD of its own. Card
  `research/UNITY-20260927-039-gtk4-menu-nonempty-preload/` on branch b/UNITY-20260927-039.

**Base:** unity-gtk4-menu 0.13 (`d377096`). Line numbers are 0.13's `src/unity-gtk4-menu.c`.

**Points C set for part C (-039):**
1. Which binary package ships the conffile, with a proposal and its reason. A new binary name would need May's
   approval as a first publication.
2. With gtk-nocsd turned off or not installed, the snippet works alone.
3. After remove (not purge) the conffile stays. It must then do nothing and never preload a missing path.
51gtk-nocsd (A's package) is not changed.

## What 0.13 does

- At realize, `find_menu_model` (:601) ranks every menu button and popover menu bar of the window by:
  1. shown (`is_shown`, :391: visible and child-visible up to the root);
  2. primary;
  3. app./win. items (`reachable_items`);
  4. tree order.
- `look` (:1635) copies the best one into `rec->inner` and starts following that model. Its `items-changed`
  triggers one idle rebuild (`rebuild_idle`, :1446), which syncs the copy in place (`sync_menu`).
- The choice is never made again. A window with no menu at realize waits, and a late look runs on the map of a menu
  button (the map shims, :1740). Once the menubar is filled, the shims return at once (`waiting_count == 0`).
- `rebuild_idle` calls `add_stand_ins` (:1423) on every rebuild. That runs `find_menu_model` on every other
  GtkApplicationWindow of the application before it checks whether any action name is new.

## A. Follow the shown menu (UNITY-20261013-028)

### Triggers

There are two, and neither uses a timer.

1. **A menu widget is mapped in the followed window.**
   - The map shims stay installed after a fill: `look` installs them on success, as `waiter_add` does now.
   - `late_mapped` (:1755) gets a second branch, taken when the root is `rec->window` of a record in state
     OURS_FILLED and the widget is not `rec->owner`.
   - The record is found through `gtk_window_get_application(root)` and `record_for`. A window of another
     application, or a second window of the same one, schedules nothing.
   - The branch schedules one relook idle per record (`rec->relook_idle`), coalesced like the rebuild.
   - **Filter, before scheduling:** the mapped widget passes `late_owner_ok` (:453): a header bar or titlebar
     ancestor, and no AdwDialog, AdwBottomSheet or GtkPopover ancestor.
   - Why the filter: list rows with menu buttons map and unmap while scrolling. Without it, every scroll step in a
     followed window would cost a full tree walk.
2. **The current owner is unmapped.**
   - `start_following` connects `unmap` on `rec->owner`, and `stop_following` disconnects it.
   - Without this trigger:
     - a GtkStack crossfade maps the new page while the old one is still shown, and the idle would compare the two
       mid-transition;
     - closing Console's tab overview maps nothing at all.

The counter of waiting windows for the shim's early return becomes `waiting_count + following_count`.
`following_count` counts records in OURS_FILLED with a live window.

### The relook

Run in the idle, on `rec->window` only:
- Return if the record is not OURS_FILLED, or its window or owner is gone. The second case is already handled, as in
  `rebuild_idle`.
- **Candidates:** collected with the late look's filter (`consider`, :502):
  - shown;
  - `late_owner_ok`;
  - at least one app./win. item;
  - not ours.

  It is a third mode of `struct look` (`relook`), not `late = 1`. `collect_menus` would otherwise call `watch_late` on
  every button without a model (:541-547), connecting handlers on a window that does not wait.
- **R** is the best candidate by the 0.13 ranking. Every candidate is shown here, so the ranking reduces to primary,
  then items, then tree order.
- **C** is the current source: its owner's `is_shown` now, its primary flag, and its item count. Primary and items
  are kept in the record at the fill and at each switch.

**Switch rule:**

| C now | switch to R when | otherwise |
|---|---|---|
| no R | never | keep C |
| R's model is C's | never (nothing to do) | |
| C shown | R outranks C: R primary and C not, or the same primary flag and more items | keep C (ties keep C) |
| C hidden | R is primary, **or** R has at least as many items as C | keep C |

Why the last row is not simply "the best shown wins". Two measured cases pull in opposite directions, and items are
the 0.13 rationale for telling a main menu from a secondary one:

| case | C | R | wanted | the row gives |
|---|---|---|---|---|
| Papers: start view → document view (README) | the start page's `app_menu` (primary, 3), hidden | the sidebar's `sidebar_menu` (primary, 5) | switch | primary: switch |
| Papers: the sidebar collapsed (`doc.show-sidebar`) | `sidebar_menu` (primary, 5), hidden | the Document Menu (not primary, 2 app./win. of 13; 11 are `doc.*`) | keep: the main menu is only collapsed, and the other is 11 dead items | 2 < 5: keep |
| Papers: the sidebar shown again | `sidebar_menu` | `sidebar_menu` (mapped again) | nothing | same model |
| Console: tab overview opened (`win.show-tabs-desktop`) | `primary_menu` (not primary, 6), shown | the overview's `secondary-menu` (primary, 3: New Window, Fullscreen, Leave Fullscreen) | follow what F10 opens there | primary: switch |
| Console: tab overview closed | the overview's menu (primary, 3), hidden | `primary_menu` (not primary, 6) | back to the main menu | 6 ≥ 3: switch |

The Console rows are from gnome-console 49.2's `kgx-window.ui`. They are to be measured on target2 (Tests, T3).

### The switch

1. Unwatch the old source. Keep `rec->names`, the old source's action names, so the stand-in pass below sees which
   names are new.
2. Set source, owner, window, primary and items to R's, and connect `unmap` on the new owner.
3. Run the `rebuild_idle` body:
   - `clean_model` of the new source, with stand-ins for this window;
   - `sync_menu` into `rec->inner` in place;
   - the stand-in pass for other windows (B);
   - new names;
   - watch the new source.
4. The holder item and its label stay. The exporter sends `Changed` only for what differs, as in 0.13.
5. Log line: `switched to the shown menu (candidate N of M)`.

Stand-ins of the old menu stay in the window's action map, as 0.13 leaves them after a rebuild. Their owner pointers
are weak.

### Edge cases, stated

- **Open panel menu.** A switch while a panel menu of this application is open replaces its items in place. A switch
  needs a map or unmap in the window, which in practice means the user acted in the window, so the panel menu is
  closed by then. Not otherwise guarded.
- **Ping-pong.**
  - Map and unmap are the only triggers, and a switch maps nothing, so a relook cannot trigger another.
  - A crossfade gives at most two relooks: one at the map, one at the old owner's unmap.
- **The application takes over the menubar** (TAKEN), or the window goes: the relook returns, and `stop_following`
  disconnects `unmap`.
- **Several windows of one application.** Only `rec->window` is followed, as in 0.13. Focus-following, per-window
  menus are out of scope (DECISIONS 2026-09-26: "estimated, not built").

### Not in scope, proposed as a follow-up

Papers' Document Menu is `doc.*`, a group inserted with `gtk_widget_insert_action_group`. 0.13 cannot reach it, and
neither does 0.14.
- Our gtk-nocsd series part (a) did reach such groups, by hooking that entry point (DECISIONS 2026-09-26).
- In unity-gtk4-menu that is a new task, with its own existing-component question. I'll propose it to C.

## B. The stand-in pass, bounded (UNITY-20261013-030)

- `add_stand_ins` first computes the names that are new: in `names` and not in `rec->names`.
- With none, it returns before looking at any window. That covers relabels, toggles, enabled-state changes and
  reorders, the common case: Nautilus's Undo relabel keeps `win.undo`.
- With new names, the per-window loop runs as now. It is only reached when the menu's action set changes, which also
  includes the switch in A.

Weighed:
- **A cached owner per window.** Not taken: the owner can change with A in other windows too, and the cache would
  need its own invalidation for a case that new names make rare.

Measured (T5):
- the number of `find_menu_model` calls per rebuild with N windows, from the debug log;
- 0.13 against 0.14.

## C. The Xsession snippet (UNITY-20260927-039)

### Where it runs, and why there

`/etc/X11/Xsession.d/52unity-gtk4-menu`: after `51gtk-nocsd` and before `90x11-common_ssh-agent` and
`95dbus_update-activation-env`.

**Our library must come first.** With gtk-nocsd first in LD_PRELOAD, our `g_module_symbol` is never reached
(UNITY-20261013-013). Both libraries define it (`nm -D`: `g_module_symbol` is the only common symbol). The
environment.d order already puts ours first.

A snippet before 51 would also work, and could leave STARTUP alone. But 51 then prepends gtk-nocsd ahead of ours in
exactly the -039 case. So it runs after 51 and puts ours in front.

### What it does

The prototype, as proposed for the package:

```sh
if [ -r /usr/lib/environment.d/60-unity-gtk4-menu.conf ] &&
    [ -n "${LD_PRELOAD-}" ]; then
  # found: ours in any form (bare name or path) among the ':'/blank-separated entries
  # off: an environment.d/60-unity-gtk4-menu.conf of the user's or the administrator's in
  #      /etc, /run, /usr/local/lib or ${XDG_CONFIG_HOME:-$HOME/.config}, as 51gtk-nocsd checks its own
  if neither:
    LD_PRELOAD='/usr/$LIB/libunity-gtk4-menu.so.0':$LD_PRELOAD; export LD_PRELOAD
    case $STARTUP in "env LD_PRELOAD=$old "*) replace that first word's value with the new one ;; esac
fi
```

(The full prototype is 51 lines and uses the `_ugm_` prefix for its variables, all unset at the end.)

- **Only when the session has an LD_PRELOAD.** Without one, 95dbus exports nothing, and the user manager keeps
  environment.d's value with ours in it. When 51 is present, it has also imported that value. So there is nothing to
  do (case A, H).
- **STARTUP.** 51gtk-nocsd passes its value into a setgid ssh-agent as the first words of STARTUP:
  `env LD_PRELOAD=<value> `. An outer `env` of ours would be overridden by that inner one, so the snippet replaces
  exactly that prefix when it is there.
  - On target2 the Unity session does not go through it: the session tree has no ssh-agent above it, and everything
    runs under `systemd --user`.
  - It matters for consistency, and for sessions that do.
  - When the prefix is not there (no gtk-nocsd), STARTUP is left alone, as before.
- **An entry the user placed** (`…:libunity-gtk4-menu.so.0` anywhere in their list) is found and left where they put
  it (case F).

### C's points

**1. The binary package: `libunity-gtk4-menu0`. A new binary package is not proposed.**

Reasons:
- **The precedent in the same stack:**
  - `libgtk-nocsd0` (`Multi-Arch: same`, published since gtk-nocsd +unity2) ships the conffile
    `/etc/X11/Xsession.d/51gtk-nocsd`, beside `/usr/lib/environment.d/50-gtk-nocsd.conf`;
  - the two preload libraries' snippets would stay alike: the same package shape and the same guard.
- **It is not a library in the usual sense:**
  - nothing links it, and it already carries `package-name-doesnt-match-sonames`;
  - it ships non-library files today: environment.d and a gschema.
- **The SONAME argument cuts both ways.** The snippet names `.so.0`, so a future `libunity-gtk4-menu1` would need a
  new snippet anyway. With `Multi-Arch: same`, the conffile is byte-identical on every architecture, as 51gtk-nocsd
  is. The content does not depend on the architecture: `$LIB` is left to the loader.
- **What a separate package would cost:**
  - environment.d would have to move too, otherwise the two halves are split: Breaks/Replaces on the old library
    version;
  - something has to pull the new package on upgrade, but `unity-session` depends on the library, not on a new name;
  - a first publication that needs May.

  The design does not need any of that.
- **If C or May prefers the separate package, the shape would be:**
  - `unity-gtk4-menu` (Architecture: all) with environment.d, the snippet and the gschema;
  - Depends: libunity-gtk4-menu0 (= ${binary:Version}) is not possible from arch:all, so `>= ${source:Version}`;
  - the library Recommends it, and `unity-session` Depends on it.

  It is stated here so the choice is visible, not proposed.

**2. Alone, without gtk-nocsd.**

Prototype sourced on target2 by dash, after the installed `51gtk-nocsd` (4.8-1+unity5) where present.
`xsession/cases.sh`, `logs/04-xsession-cases.txt`:

| case | session LD_PRELOAD | after the snippet | STARTUP |
|---|---|---|---|
| A: none | unset (51 imports the user manager's `ours:nocsd`) | unchanged | unchanged |
| B: the -039 case | `libm.so.6` | `ours:nocsd:libm.so.6` | 51's prefix rewritten to the same value |
| C: gtk-nocsd turned off (`~/.config/environment.d/50-gtk-nocsd.conf`) | `libm.so.6` | `ours:libm.so.6` | 51's prefix rewritten |
| D: no 51gtk-nocsd | `libm.so.6` | `ours:libm.so.6` | unchanged (no prefix) |
| E: unity-gtk4-menu turned off (`…/60-unity-gtk4-menu.conf`) | `libm.so.6` | `nocsd:libm.so.6`, ours not added | unchanged |
| F: ours there already (bare, after an old `~/.xsessionrc`) | `libunity-gtk4-menu.so.0:libm.so.6` | unchanged (51 wrote it as a path, after nocsd) | unchanged |
| G: entries separated by a blank | `libm.so.6 libdl.so.2` | `ours:nocsd:libm.so.6:libdl.so.2` | rewritten |
| H: none, no 51 | unset | unset, not exported | unchanged |

No `_ugm_` variable is left in any case.

**3. After remove.**
- `/usr/lib/environment.d/60-unity-gtk4-menu.conf` is not a conffile, so remove deletes it. The snippet's guard is
  `[ -r ]` on that file, as 51gtk-nocsd guards on its own, so the snippet does nothing.
- Prototype, file moved away (case R): `libm.so.6` → 51's `nocsd:libm.so.6` is left unchanged by the snippet.
- In the same harness, R2 (no session LD_PRELOAD) shows ours. That comes from 51 importing the **running** user
  manager, which was started while the file existed. A real login after remove starts a manager without it. The
  package test checks this (T7).
- Multi-arch partial removal (amd64 removed, i386 kept): environment.d stays, because the file is shared, while the
  amd64 library is gone. That limit already belongs to the environment.d path form May accepted on 12.10; the
  snippet adds nothing to it.

Upgrade from 0.13: the conffile is new. dpkg installs it, and no maintscript is needed. It takes effect at the next
login. Purge removes it.

## Weighed: does this belong in an existing component?

- **A and B:**
  - unity-gtk4-menu is the component that exports GTK4 menus. The shipped gtk-nocsd has no menu code. The same
    mechanism exists in our gtk-nocsd series and upstream GTK-NoCSD main, which we do not ship (UNITY-20261012-004).
  - Taking it from there would be the 4.8+git snapshot weighed and not taken in that card.
- **C:**
  - Changing 51gtk-nocsd to keep the user manager's value also when the session has its own was weighed in -039. It
    is gtk-nocsd's script and gtk-nocsd's scope (UNITY-20260927-022), and C ruled it out here.
  - The 90atk-adaptor precedent: each library adds its own entry.

## Tests

latetest (Xvfb, both preload forms, `G_DEBUG=fatal-criticals`), as in 0.13. Then target2.

- **23. Stack switch.** A window with a GtkStack:
  - page 1 with a primary menu (3 app. items) and page 2 with a primary menu (5 items);
  - fill on page 1, switch to page 2;
  - expect one relook, `inner` synced to page 2's items, the holder unchanged, and a D-Bus client sees `Changed`,
    not a new `Start`;
  - back to page 1: switched back (page 1 shown, page 2 hidden).
- **24. Collapse.**
  - page 2 also has a non-primary menu with 1 app. item and 10 items of an inserted group;
  - page 2's primary hidden (`gtk_widget_set_visible(FALSE)`) gives no switch, and visible again gives no switch;
  - a control with the "best shown wins" rule (a test flag in the test only, not in the library) would switch. That
    shows the case tests the rule.
- **25. Console's shape.**
  - main: non-primary, 6 items; overlay: primary, 3 items;
  - the overlay shown switches to it, and hidden switches back.
- **26. Crossfade.** A GtkStack with `crossfade`, 200 ms: at most two relooks, and the final copy is page 2's.
- **27. Filtered maps.** 1000 list-row menu buttons mapped and unmapped (a GtkListBox in the content, outside any
  header bar) give zero relooks.
- **28. Lifetime.**
  - the window destroyed with a relook idle pending: no critical (and valgrind);
  - the application sets its own menubar after the fill, then a page switch: no relook, TAKEN kept;
  - the old owner finalised after a switch: `unmap` disconnected, no handler on a dead object.
- **29 (B).**
  - 10 windows, 100 relabels: `find_menu_model` runs 0 times for other windows (debug log), against 0.13's 1000;
  - a relabel that adds a new action: 9 calls, and the stand-in appears (case 20 unchanged).
- **T1. Papers** on target2 (`probe.sh startview`):
  - after Ctrl+O the export is `sidebar_menu`: Open…, Night Mode, Keyboard Shortcuts, Help, About;
  - the sidebar collapsed (F9): unchanged;
  - shown again: unchanged.
- **T2. Papers with a PDF** at start (`withdoc`): at realize candidate 1 is chosen (start page). By the time the
  window is mapped, the document view's sidebar maps, so a relook switches. Expected: `sidebar_menu`.
- **T3. Console:** tab overview open and closed (Ctrl+Shift+O, Escape). Each switch is confirmed in the debug log and
  the export (`menudump.py`), and the HUD finds "Новое окно" in both states.
- **T4. Regression:**
  - latetest 1-22;
  - `order-0.9.sh` unchanged;
  - Nautilus Undo (-008 target 4);
  - Pinta late fill;
  - the -1013-024 survey of 13 applications: same choice at realize, and any switch logged and checked.
- **T5 (B).** Nautilus with 3 windows, 20 renames: rebuild log lines and `find_menu_model` calls, 0.13 against 0.14.
- **T6 (C), sessions on target2, cold:**
  - -039 case B: `~/.xsessionrc` `export LD_PRELOAD=libm.so.6`. The user manager, compiz and gnome-calculator have
    `ours:nocsd:libm.so.6`, and the calculator exports its menubar (the -039 `probe.sh`). The control and the 0.13
    run are already logs/01 and 03 of -039;
  - case C: gtk-nocsd turned off by the user;
  - case A: no `~/.xsessionrc`, the user manager's value as before.
- **T7 (C), remove:**
  - `apt-get remove libunity-gtk4-menu0` together with what depends on it. If unity-session must go, the test runs
    `dpkg -r --force-depends` on the test machine only and says so;
  - the conffile stays; after a cold login with `~/.xsessionrc` libm, LD_PRELOAD has no entry of ours and no
    `cannot be preloaded` line appears in the session journal;
  - then reinstall.
- **Control:** 0.13 fails 23, 25, T1, T2 and T3, and has no snippet for T6.

## Packaging

- Version 0.14 (native).
- `data/52unity-gtk4-menu`, installed by the Makefile to `$(DESTDIR)/etc/X11/Xsession.d/`. dh treats files under
  /etc as conffiles.
- `debian/control`: the description gets one sentence on the X session snippet.
- PATCHES/DECISIONS entries with the release, as before.

## Questions for the Challenger

1. The switch rule's last row (C hidden: R primary, or at least as many items). Is there a measured or plausible
   application where it keeps a dead menu, or flips to a wrong one?
2. Filtering map triggers by `late_owner_ok`: a main menu outside any header bar (yelp keeps its header bar in the
   content, which passes) would not trigger a relook on map. It would still be found at the current owner's unmap.
   Acceptable?
3. C, point 1: `libunity-gtk4-menu0`, or the separate package?
