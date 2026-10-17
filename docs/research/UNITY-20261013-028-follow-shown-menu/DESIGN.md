# unity-gtk4-menu 0.14 design: follow the shown menu (-028), bound the stand-in pass (-030), Xsession snippet (-039)

Agent B, 2026-10-17. **Round 3**, for the Design Challenger. Rounds 1 and 2 were REVISE (README, "Design review");
the tables at the end say where each finding is answered. No package code exists. The Xsession snippet's prototype
is `xsession/52unity-gtk4-menu`, sourced on target2 for part C's facts.

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
   - `late_mapped` (:1755) gets a second branch, after the waiter branch. It runs when:
     - the root is a GtkWindow (`is_a`, checked before `gtk_window_get_application`);
     - its application's record (`record_for`) is OURS_FILLED;
     - `rec->window` is that root;
     - the widget is not `rec->owner`.

     A window of another application, or a second window of the same one, schedules nothing.
   - The branch schedules one relook idle per record (`rec->relook_idle`), coalesced like the rebuild.
   - **Filter, before scheduling:** the mapped widget passes `late_owner_ok` (:453). Its `in_titlebar` is computed
     for the map, not taken from a look: 1 when the widget has an ancestor equal to `gtk_window_get_titlebar(root)`.
     That matters where the titlebar is not itself a header bar (round-1 #7).
   - Why the filter: list rows with menu buttons map and unmap while scrolling. Without it, every scroll step in a
     followed window would cost a full tree walk.
2. **The current owner is unmapped.**
   - `start_following` connects `unmap` on `rec->owner` and keeps the handler id in the record.
   - `stop_following` disconnects it while the owner is alive.
   - The id is zeroed when the weak `owner` pointer clears: the owner's finalize drops its handlers itself.
   - Without this trigger:
     - a GtkStack crossfade maps the new page while the old one is still shown, and the idle would compare the two
       mid-transition;
     - closing Console's tab overview maps nothing at all.

**The shim's early return** (round-1 #6): 0.13 returns at once while no window waits (`waiting_count == 0`). That
gate is dropped. The second branch costs:
- `gtk_widget_get_root`;
- one `is_a`;
- `gtk_window_get_application`;
- one `g_object_get_data`;

per map of a menu button or popover menu bar, and only once the shims are installed, which happens at the first fill
or wait in the process.

### The relook

Run in the idle, on `rec->window` only:
- Return if the record is not OURS_FILLED or its window is gone.
- **An owner that is gone is not a reason to stop** (round-1 #1, round-2 #1 and #2). An application can destroy the
  old view instead of hiding it: a page popped from an AdwNavigationView, or `set_child` with a new view. The relook
  then runs after the unmap with `rec->owner == NULL`.
  - A gone C has no claim, and the best shown candidate R wins whatever its flags.
  - If there is no R yet, because the new view is built later (an asynchronous load, a pop now and a push later), the
    record becomes **orphaned**:
    - the source is unwatched and released, and the owner is NULL;
    - `rec->window` and the record's OURS_FILLED state are kept, and the copy stays exported as it is, as 0.13
      leaves it;
    - the window is still followed, so the next qualifying map in it schedules a relook, which adopts R.
  - The record stops following only when the window goes or the application takes the menubar (TAKEN).
- **`rebuild_idle` with the owner gone** (:1453-1457): today it stops following. In 0.14 it orphans the record as
  above, and stops only when the window is gone.
- **Candidates** are collected with `look.late = 0`, which adds no `watch_late` (that runs only when `lk->late`,
  :541-547). The collection is then filtered here:
  - shown (`is_shown`);
  - at least one app./win. item;
  - not ours (already in `consider`);
  - and either `late_owner_ok`, or the owner is the one chosen at realize (`rec->first_owner`, a weak pointer set at
    the fill).

  The late look's narrower set keeps AdwDialog content, list rows and popovers out. The realize-time owner is
  admitted as well, because 0.13 chose it without that filter, for example a popover menu bar in the content. Without
  this exception it could never come back (round-1 #5).
- **R** is the best remaining candidate by the 0.13 ranking. Every candidate is shown, so the ranking reduces to
  primary, then items, then tree order.
- **C** is the current source: its owner's `is_shown` now (hidden when the owner is gone), its primary flag and its
  item count. Primary and items are kept in the record at the fill and at each switch.

**Switch rule** (round 2: the last two rows changed, round-1 #4):

| C now | switch to R when | otherwise |
|---|---|---|
| no R | never | keep C; if C's owner is gone, the record is orphaned (above) |
| C's owner gone | always: the best shown candidate wins | |
| R's model is C's, same owner | never (nothing to do) | |
| R's model is C's, another owner, and C's owner hidden or gone (round-2 #3) | always: the owner is adopted | |
| C shown | R outranks C: R primary and C not, or the same primary flag and more items | keep C (ties keep C) |
| C hidden, C primary | R is primary, **or** R has at least as many items as C | keep C |
| C hidden, C not primary | always: the best shown candidate wins | |

Why the item test stays for a primary C. Two measured cases pull in opposite directions, and items are the 0.13
rationale for telling a main menu from a secondary one:

| case | C | R | wanted | the rule gives |
|---|---|---|---|---|
| Papers: start view → document view (README) | the start page's `app_menu` (primary, 3), hidden | the sidebar's `sidebar_menu` (primary, 5) | switch | R primary: switch |
| Papers: the sidebar collapsed (`doc.show-sidebar`) | `sidebar_menu` (primary, 5), hidden | the Document Menu (not primary, 2 app./win. of 13; 11 are `doc.*`) | keep: the main menu is only collapsed, and the other is 11 dead items | C primary, 2 < 5: keep |
| Papers: the sidebar shown again | `sidebar_menu` | `sidebar_menu` (mapped again) | nothing | same model |
| Console: tab overview opened (`win.show-tabs-desktop`) | `primary_menu` (not primary, 6), shown | the overview's `secondary-menu` (primary, 3: New Window, Fullscreen, Leave Fullscreen) | follow what F10 opens there | R primary, C not: switch |
| Console: tab overview closed | the overview's menu (primary, 3), hidden | `primary_menu` (not primary, 6) | back to the main menu | C primary, 6 ≥ 3: switch |
| no primary anywhere (round-1 #4): main 6 items; a page shows a header-bar menu of 8 `win.*` | main (6), shown | page menu (8) | switch while the page shows | more items: switch |
| the same, page left | page menu (not primary, 8), hidden | main (6) | back | C not primary: switch |

The Console rows are from gnome-console 49.2's `kgx-window.ui`. They are to be measured on target2 (Tests, T3).

### The switch

1. Cancel a pending `rebuild_idle` (round-1 #6) and unwatch the old source. Keep `rec->names`, the old source's
   action names, so the stand-in pass below sees which names are new.
2. Set source, owner, primary and items to R's, and connect `unmap` on the new owner. The window is the same.
3. Run the `rebuild_idle` body:
   - `clean_model` of the new source, with stand-ins for this window (see the next section);
   - `sync_menu` into `rec->inner` in place;
   - the stand-in pass for other windows (B);
   - new names;
   - watch the new source.
4. The holder item and its label stay. The exporter sends `Changed` only for what differs, as in 0.13.
5. Log line: `switched to the shown menu (candidate N of M)`.

**The same model behind a new owner** (an application rebuilt its header bar from the same `GMenuModel`) takes the
same path. The source does not change, `sync_menu` finds nothing to replace and emits nothing, and the stand-in check
below rebinds each stand-in to the new owner. The log line says `owner adopted`.

### Stand-ins reused across a switch (round-1 #2)

- `proxy_for` (:876) reuses a stand-in that is already in the window's map under the same local name (:893). That
  stand-in keeps its old `owner` and `holder` and its `notify::` binding.
- 0.13 never hits this case, because the owner never changes within a window. After a switch, two pages of one class
  with their own header bars would activate the old, hidden widget and mirror its state.
- **0.14:** each stand-in's `struct proxy` is also kept on its action (`g_object_set_data`). On a hit, `proxy_for`
  compares it with what it has just found:
  - **holder:** the result of `find_class_action(owner)`, computed before the lookup as it is now;
  - **owner:** the new owner.

  If either differs, the old action is removed from the map, and the new one is created as on a miss.
- **The old action may outlive its removal** (round-2 #4): an activation in progress, or the exporter or muxer during an
  emission, can still hold a reference. Its `proxy_free` then runs after the new stand-in exists. When the holder is
  the same, clearing the holder's `PROXY_KEY` by name would cut the new action off from
  `gtk_widget_action_set_enabled` forwarding (:2181). So `struct proxy` also keeps its action (a plain pointer, no
  reference), and `proxy_free` clears `PROXY_KEY` only if it still points to that action.
- In 0.13's paths the hit always matches, so nothing changes there.

### Lifetime (round-1 #6)

- `relook_idle` is removed in `stop_following`, as `rebuild_idle` is (:1237). `record_free` runs `stop_following`, so
  an application finalised with a relook pending has no idle left.
- `first_owner` is a weak pointer, cleared and released in `stop_following`.
- The `unmap` handler id is ignored once `owner` is NULL, and disconnected only on a live owner. GObject drops a
  disposed object's handlers itself (round-2 #5).

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
- In unity-gtk4-menu that is a new task with its own existing-component question: UNITY-20261017-007 (BACKLOG),
  card `research/UNITY-20261017-007-gtk4-menu-inserted-groups/`.

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

The 51gtk-nocsd it runs after is gtk-nocsd 4.8-1+unity5's, the one installed on target2 (md5
`76e7ba88d91d64fdba5c49392e218153`, as in dpkg's conffile record). Source:
`packages/gtk-nocsd/debian/51gtk-nocsd` at `6aab167` (A's worktree for UNITY-20261013-029). The base checkout's copy
is older (+unity3: bare names, no opt-out check) and is not what the claims here refer to (round-1 #8).

### What it does

The prototype, as proposed for the package, is `xsession/52unity-gtk4-menu` (62 lines; round-1 #8). In short:

```sh
if [ -r /usr/lib/environment.d/60-unity-gtk4-menu.conf ] && [ -n "${LD_PRELOAD-}" ]; then
  # off: an environment.d/60-unity-gtk4-menu.conf of the user's or the administrator's in
  #      /etc, /run, /usr/local/lib or ${XDG_CONFIG_HOME:-$HOME/.config}, as 51gtk-nocsd checks its own;
  #      then the list is left as it is
  # otherwise: every other ':'/blank-separated entry in its order; every entry of ours taken out, and one put first:
  #      a copy of ours from outside /usr (a build of one's own) if there is one, else '/usr/$LIB/libunity-gtk4-menu.so.0'
  #      (the installed library by bare name or any /usr path becomes this form)
  # if that differs from LD_PRELOAD: export it, and replace 51's "env LD_PRELOAD=<old> " at the head of STARTUP
fi
```

Its variables use the `_ugm_` prefix and are all unset at the end.

- **Only when the session has an LD_PRELOAD.** Without one, 95dbus exports nothing, and the user manager keeps
  environment.d's value with ours in it. When 51 is present, it has also imported that value. So there is nothing to
  do (cases A, H).
- **Ours always first** (round-1 #3). An entry of ours found behind gtk-nocsd is moved to the front, and duplicates
  are dropped.
  - Case F: an old `~/.xsessionrc` named ours bare. 51 then wrote it as a path behind gtk-nocsd, and with that order
    our `g_module_symbol` is never reached. gtk-nocsd resolves the real one by name, not by chaining:
    `GTK-NoCSD.c`:1183-1186 in our series.
  - Moving it is what the user asked for by naming it. Leaving it would keep it loaded and inert for gjs and
    PyGObject applications.
  - A copy of ours preloaded from outside /usr (a developer's own build, `/opt/…`) is kept and moved first instead of
    the installed one. Adding the installed one too would load two copies hooking the same classes (round-2 #6).
- **STARTUP.** 51gtk-nocsd passes its value into a setgid ssh-agent as the first words of STARTUP:
  `env LD_PRELOAD=<value> `, with `:` separators only. An outer `env` of ours would be overridden by that inner one,
  so the snippet replaces exactly that prefix when it is there. Nothing runs between 51 and 52 (`ls
  /etc/X11/Xsession.d` on target2: `51gtk-nocsd`, then `55cinnamon-session_gnomerc`).
  - On target2 the Unity session does not go through it: the session tree has no ssh-agent above it, and everything
    runs under `systemd --user`.
  - It matters for consistency, and for sessions that do.
  - When the prefix is not there, STARTUP is left alone.
  - **Stated limit** (round-1 #10): without 51 (case D), a session that does start a setgid ssh-agent loses the
    session's LD_PRELOAD inside it, ours included, exactly as with 0.13 today. The user manager still gets ours
    through 95dbus. Adding our own prefix there is not proposed: it would be the first STARTUP edit of ours, for a
    session the library does nothing in (it acts only in Unity, and Unity runs its applications from the user
    manager).

### C's points

**1. The binary package: `libunity-gtk4-menu0`. A new binary package is not proposed.** C accepted this on
2026-10-17, with libgtk-nocsd0/51gtk-nocsd as the precedent, and the Challenger agreed in round 1. The deviation from
Debian Policy 8.2 (files that do not change with the SONAME belong in another package) goes into DECISIONS with the
release. A SONAME bump would need the arch:all split sketched below.

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
`xsession/cases.sh`; round 1 `logs/04-xsession-cases.txt`, round 2 `logs/05-xsession-cases-round2.txt`, round 3
`logs/06-xsession-cases-round3.txt` (the same 12 results, and K and L). Rounds 2 and 3 ran
on the live archive (InRelease 2026-10-17 07:48:02 UTC) after a cold boot, so the user manager's value was built from
the installed environment.d files.

| case | session LD_PRELOAD | after the snippet | STARTUP |
|---|---|---|---|
| A: none | unset (51 imports the user manager's `ours:nocsd`) | unchanged | unchanged |
| B: the -039 case | `libm.so.6` | `ours:nocsd:libm.so.6` | 51's prefix rewritten to the same value |
| C: gtk-nocsd turned off (`~/.config/environment.d/50-gtk-nocsd.conf`) | `libm.so.6` | `ours:libm.so.6` | 51's prefix rewritten |
| D: no 51gtk-nocsd | `libm.so.6` | `ours:libm.so.6` | unchanged (no prefix) |
| E: unity-gtk4-menu turned off (`…/60-unity-gtk4-menu.conf`) | `libm.so.6` | `nocsd:libm.so.6`, ours not added | unchanged |
| F: ours there already (bare, after an old `~/.xsessionrc`) | `libunity-gtk4-menu.so.0:libm.so.6` | 51 gives `nocsd:ours:libm`; the snippet gives `ours:nocsd:libm.so.6` (round 1 left it) | rewritten |
| G: entries separated by a blank | `libm.so.6 libdl.so.2` | `ours:nocsd:libm.so.6:libdl.so.2` | rewritten |
| H: none, no 51 | unset | unset, not exported | unchanged |
| I: ours twice, both behind gtk-nocsd | `libm.so.6:/usr/$LIB/…menu.so.0:libunity-gtk4-menu.so.0` | `ours:nocsd:libm.so.6`, once | rewritten |
| J: ours first already, no 51 | `/usr/$LIB/…menu.so.0:libm.so.6` | unchanged | unchanged |
| K: a build of ours in /opt behind libm, and the installed one bare | `libm.so.6:/opt/ugm/…menu.so.0:libunity-gtk4-menu.so.0` | `/opt/ugm/…menu.so.0:nocsd:libm.so.6` | rewritten |
| L: the installed one by its full multiarch path | `/usr/lib/x86_64-linux-gnu/…menu.so.0:libm.so.6` | `ours:nocsd:libm.so.6` (path form) | rewritten |
| R: removed, `libm.so.6` | | 51's `nocsd:libm.so.6`, unchanged | unchanged |
| R2: removed, none | | `ours:nocsd`, from 51's import of the running manager (see point 3) | unchanged |

No `_ugm_` variable is left in any case.

**3. After remove.**
- `/usr/lib/environment.d/60-unity-gtk4-menu.conf` is not a conffile, so remove deletes it. The snippet's guard is
  `[ -r ]` on that file, as 51gtk-nocsd guards on its own, so the snippet does nothing.
- Prototype, file moved away (case R): `libm.so.6` → 51's `nocsd:libm.so.6` is left unchanged by the snippet.
- In the same harness, R2 (no session LD_PRELOAD) shows ours. That comes from 51 importing the **running** user
  manager, which was started while the file existed. A real login after remove starts a manager without it, as long
  as the user manager has exited. Otherwise R2's import of the old value can preload a missing path, through 51
  rather than ours. T7 therefore logs in cold, after a reboot (the manager does not linger) (round-1 #10).
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
- **26. No primary anywhere** (round-1 #4): main 6 items, a page's header-bar menu with 8 `win.*` items. The page
  shown switches to its menu, and the page left switches back.
- **27. Destroyed, not hidden** (round-1 #1, round-2 #1, #2):
  - (a) the page with the current primary menu removed from its stack and destroyed, while another page with a
    non-primary menu of fewer items is shown: the relook switches to it;
  - (b) the page destroyed with nothing else shown: the record is orphaned (log line), the copy unchanged. After the
    idle has run, a new page with a menu is added and shown: one relook, switched;
  - (c) as (b), then the window closed: the record stops following, and no handler or idle remains (valgrind).
- **28. Two instances of one class** (round-1 #2, round-2 #4): two pages, each a widget of the same class with a
  class action in its menu and its own header-bar button.
  - After the switch, activating the item from D-Bus reaches the page now shown, and a property action's state
    mirrors that page's property.
  - Again with an extra reference held on the old action across the switch, then the new page's
    `gtk_widget_action_set_enabled` toggled: the new stand-in follows it.
- **29. A realize-time owner outside a header bar** (round-1 #5): a popover menu bar in the content chosen at
  realize, then a primary header-bar button shown (switch) and hidden again (back to the menu bar).
- **30. The same model, a new owner** (round-2 #3): the header bar rebuilt with a new button on the same
  `GMenuModel`, the old one destroyed. The owner is adopted (log line), no `Changed` on D-Bus, and a class-action item
  activates on the new button's widget.
- **31. Crossfade.** A GtkStack with `crossfade`, 200 ms: at most two relooks, and the final copy is page 2's.
- **32. Filtered maps.** 1000 list-row menu buttons mapped and unmapped (a GtkListBox in the content, outside any
  header bar) give zero relooks.
- **33. Lifetime.**
  - the window destroyed with a relook idle pending: no critical (and valgrind);
  - the application sets its own menubar after the fill, then a page switch: no relook, TAKEN kept;
  - the old owner finalised after a switch: `unmap` disconnected, no handler on a dead object;
  - the application finalised with a relook idle pending: no idle runs afterwards (valgrind);
  - a switch with a rebuild idle pending: the rebuild is cancelled, and one sync happens.
- **34 (B).**
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
- **T6 also, case F:** `~/.xsessionrc` with `export LD_PRELOAD=libunity-gtk4-menu.so.0:libm.so.6`. The user manager
  has ours first, and a gjs application (gnome-characters) and a PyGObject one (the -1013-013 `apps.py` set) export
  their menubar.
- **T7 (C), remove:**
  - `apt-get remove libunity-gtk4-menu0` together with what depends on it. If unity-session must go, the test runs
    `dpkg -r --force-depends` on the test machine only and says so;
  - the conffile stays; after a reboot (so the user manager starts without the environment.d file) and a cold
    login with `~/.xsessionrc` libm, LD_PRELOAD has no entry of ours and no `cannot be preloaded` line appears in
    the session journal;
  - the same without `~/.xsessionrc` (R2 for real);
  - then reinstall.
- **Control:** 0.13 fails 23, 25, 26, 27, 29, T1, T2 and T3, and has no snippet for T6.

## Packaging

- Version 0.14 (native).
- `data/52unity-gtk4-menu`, installed by the Makefile to `$(DESTDIR)/etc/X11/Xsession.d/`. dh treats files under
  /etc as conffiles.
- `debian/control`: the description gets one sentence on the X session snippet.
- PATCHES/DECISIONS entries with the release, as before.

## Questions for the Challenger (round 3)

1. Orphaned records: is anything left that keeps the window followed after it should not be, or that misses the
   window's end?

## Round-1 findings and where they are answered

| # | finding | answer |
|---|---|---|
| 1 | an owner destroyed, not hidden, stops following | "The relook": a gone owner counts as hidden C; stop only with no R; test 27 |
| 2 | stand-ins reused with the old owner/holder | "Stand-ins reused across a switch": replace on a holder or owner mismatch; test 28 |
| 3 | case F leaves ours behind gtk-nocsd | "What it does": ours always moved first, duplicates dropped; case F rerun; T6 case F with gjs and PyGObject |
| 4 | a hidden non-primary C sticks | rule rows changed; table rows 6-7; test 26 |
| 5 | a realize-time C outside header bars can never come back | `rec->first_owner` admitted as a candidate; test 29 |
| 6 | lifetime: idles, handler id, `following_count` | "Lifetime"; the gate dropped ("Triggers"); test 33 additions |
| 7 | `in_titlebar` for the map filter; `is_a` window before `get_application` | "Triggers", item 1 |
| 8 | prototype and R/R2 not in the card; the 51gtk-nocsd cited was +unity3 | `xsession/52unity-gtk4-menu`, `cases.sh ... removed`; +unity5 cited with its md5 |
| 9 | B correct | - |
| 10 | case D with ssh-agent; T7 needs the manager gone | stated limit in "What it does"; T7 reboots |

## Round-2 findings and where they are answered

| # | finding | answer |
|---|---|---|
| 1 | a gone owner with no R stops following, and a later view is never seen | "The relook": orphaned records keep the window; test 27 (b), (c) |
| 2 | a gone primary C keeps a fewer-item R out | rule row "C's owner gone": R wins; test 27 (a) |
| 3 | the same model behind a new owner | rule row and "The switch": owner adopted; test 30 |
| 4 | `proxy_free` after the new stand-in clears its key | compare-then-clear; test 28, second item |
| 5 | the handler id is not zeroed | wording in "Lifetime" |
| 6 | a developer build replaced by the installed path | kept and moved first; cases K, L (logs/06) |
| 7 | test numbering | renumbered 23-34 |
