#!/bin/sh
# LP #2160299: make a file manager that is neither Nautilus nor Nemo the
# default for inode/directory, restart compiz, report whether it survives.
# fm-default.sh set|restore
. ~/envt.sh
if [ "$1" = set ]; then
  mkdir -p ~/.local/share/applications
  printf '[Desktop Entry]\nType=Application\nName=Test FM\nExec=xterm -e ls %%U\nMimeType=inode/directory;\n' > ~/.local/share/applications/test-fm.desktop
  update-desktop-database ~/.local/share/applications 2>/dev/null
  echo "before: $(xdg-mime query default inode/directory)"
  xdg-mime default test-fm.desktop inode/directory
  echo "now: $(xdg-mime query default inode/directory)"
else
  xdg-mime default nemo.desktop inode/directory
  rm -f ~/.local/share/applications/test-fm.desktop
  echo "restored: $(xdg-mime query default inode/directory)"
  exit 0
fi
C=$(pgrep -x compiz); T=$(date +%T)
killall -1 compiz; sleep 40
echo "compiz $C -> $(pgrep -x compiz); unity7 $(systemctl --user is-active unity7); crash files: $(ls /var/crash | tr '\n' ' ')"
journalctl --since $T --no-pager | grep -E "compiz.*segfault|unity7.service: Main process exited|Failed with result" | cut -c1-160 | head
