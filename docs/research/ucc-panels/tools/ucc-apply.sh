#!/bin/bash
# A-7: change one setting per panel through the panel itself (AT-SPI action =
# a click), check that it reached the consumer, change it back. Agent A.
. ~/envt.sh; A="timeout 20 python3 -W ignore $HOME/a11y.py"
g() { gsettings get "$@" 2>/dev/null; }
eff_repeat() { xset q | grep -oE "auto repeat:\s+\w+" | awk '{print $3}'; }
eff_buttons() { id=$(xinput list --id-only "ImExPS/2 Generic Explorer Mouse"); xinput get-button-map $id | cut -d' ' -f1-3; }
eff_mute() { pactl get-sink-mute @DEFAULT_SINK@ | awk '{print $2}'; }
eff_theme() { python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk; print(Gtk.Settings.get_default().props.gtk_theme_name)' 2>/dev/null; }
t() { # panel | widget | role | revert-widget | check-cmd
  ~/ucc-open.sh $1 >/dev/null 2>&1; b=$(eval "$5"); $A click "$2" "$3" >/dev/null 2>&1; sleep 2; a=$(eval "$5")
  $A click "$4" "$3" >/dev/null 2>&1; sleep 2; r=$(eval "$5")
  echo "$1 | '$2' | before=[$b] after=[$a] reverted=[$r] | $([ "$b" != "$a" ] && [ "$b" = "$r" ] && echo APPLIED+REVERTED || echo CHECK)"; }
t keyboard "Повторять удерживаемую нажатой клавишу" "check box" "Повторять удерживаемую нажатой клавишу" 'echo "$(g org.gnome.desktop.peripherals.keyboard repeat)/$(g org.gnome.settings-daemon.peripherals.keyboard repeat) X:$(eff_repeat)"'
t mouse "Правая" "radio button" "Левая" 'echo "$(g org.gnome.settings-daemon.peripherals.mouse left-handed) X:$(eff_buttons)"'
t sound "Выключить звук" "check box" "Выключить звук" 'echo "pulse-mute:$(eff_mute)"'
t region "Разрешить разные источники для каждого окна" "radio button" "Использовать один источник для всех окон" 'echo "gkbd:$(g org.gnome.libgnomekbd.desktop group-per-window) input-sources:$(g org.gnome.desktop.input-sources per-window)"'
t datetime "Секунды" "check box" "Секунды" 'g com.canonical.indicator.datetime show-seconds'
t bluetooth "Показывать состояние Bluetooth на панели меню" "check box" "Показывать состояние Bluetooth на панели меню" 'g com.canonical.indicator.bluetooth visible'
t screen "Требовать пароль при выходе из спящего режима" "check box" "Требовать пароль при выходе из спящего режима" 'g org.gnome.desktop.screensaver ubuntu-lock-on-suspend'
t activity-log-manager "Returning from blank screen" "check box" "Returning from blank screen" 'g org.gnome.desktop.screensaver lock-enabled'
t universal-access "Подавать сигнал при нажатии модификатора" "check box" "Подавать сигнал при нажатии модификатора" 'g org.gnome.desktop.a11y.keyboard togglekeys-enable'
t appearance "Yaru" "menu item" "Yaru-dark (по  умолчанию)" 'echo "$(g org.gnome.desktop.interface gtk-theme) xsettings:$(eff_theme)"'
t sound "Отображать уровень громкости на панели меню" "check box" "Отображать уровень громкости на панели меню" 'g com.canonical.indicator.sound visible'
for p in $(pgrep -x unity-control-c); do kill $p; done
