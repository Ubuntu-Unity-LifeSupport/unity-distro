# unity-gtk4-menu: no stand-ins for action groups inserted on a widget (UNITY-20261017-007)

```yaml
task: UNITY-20261017-007
title: unity-gtk4-menu gives no stand-ins to actions of groups inserted with gtk_widget_insert_action_group
package: unity-gtk4-menu (0.13 live; 0.14 in design)
target_series: resolute
status: BACKLOG, unassigned. Facts from UNITY-20261013-028 only; nothing measured for this task yet
```

## Facts so far (agent B, 2026-10-17, from UNITY-20261013-028)

- **What the global menu can reach.** It activates only what the application exports over D-Bus: `app.*` and a
  GtkApplicationWindow's `win.*`.
  - unity-gtk4-menu 0.13 adds stand-ins in the window's action map for **class** actions
    (`gtk_widget_class_install_action`, property actions included) found on the menu's owner or its ancestors.
  - Any other prefix is left alone and logged as `<name> has a prefix the global menu cannot reach`
    (`src/unity-gtk4-menu.c`:876-889 in 0.13).
- **Papers 50.2's "Document Menu"** (`document_menu` in `shell/resources/pps-document-view.blp`) has 13 items. 11 of
  them name `doc.*` actions: Print, Sign, Open a Copy, Open With, Save As, Continuous, Dual, Odd Pages Left, Right to
  Left, Rotate, Properties. `doc` is a group Papers inserts on its document view.
  - The menu is not primary. The menu UNITY-20261013-028 makes the panel follow in the document view is the sidebar's
    `sidebar_menu` (primary, 5 app./win. items).
  - So this task does not block -028. It is about whether a second, mostly widget-scoped menu could ever be served.
  - Card: `research/UNITY-20261013-028-follow-shown-menu/README.md`, "The candidates, from Papers' source".
- **GTK 4 has no public getter for a widget's inserted groups.** The muxer is private. Activation by name works from
  the widget: `gtk_widget_activate_action_variant`. The enabled state and the parameter type do not have a public
  getter.

## Prior art: the existing-component question comes first

- Our gtk-nocsd series part (a) gave stand-ins to inserted groups by hooking `gtk_widget_insert_action_group`, and
  activated the originals with `gtk_widget_activate_action_variant` from the widget the group is on. In 44
  applications this took 10 dead items to 0 (DECISIONS 2026-09-26, "gtk-nocsd global menu gaps"; record
  `research/nocsd-gaps/`).
- That code is in our series and in upstream GTK-NoCSD main. It is not in the shipped gtk-nocsd 4.8-1+unity5, which
  has no menu code (UNITY-20261012-004, "What we ship").
- The 2026-09-26 decision said the code belongs in the gtk-nocsd parts, not duplicated in unity-gtk4-menu. Since then
  unity-gtk4-menu has become the shipped exporter (0.11-0.13). Whoever takes this task weighs the two again, with
  that change, before any design.

## Not known yet

- Which applications in the -1013-024 survey (13 GTK 4 applications) have menu items with prefixes other than app./win.
  in the menu that is chosen. The 0.13 debug log line above counts them.
