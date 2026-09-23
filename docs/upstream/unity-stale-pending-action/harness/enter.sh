#!/bin/sh
# enter.sh ROOT CMD... - run CMD inside ROOT (sudo, private mount+pid namespace)
R=$1; shift
exec sudo -n unshare --mount --pid --fork --kill-child sh -c '
  R=$0; mount -t proc proc "$R/proc" && mount --rbind /dev "$R/dev" && mount -t tmpfs tmpfs "$R/tmp" && exec chroot "$R" -- "$@"' "$R" "$@"
