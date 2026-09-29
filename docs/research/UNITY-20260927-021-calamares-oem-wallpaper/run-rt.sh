#!/bin/bash
# run-rt.sh DEBNAME ROUNDS - run rt.sh inside the b-dev chroot (own mount+pid namespace).
C=/var/tmp/sbuild-claude/b-dev
sudo unshare --mount --pid --fork bash -c "mount -t proc proc $C/proc; mount --bind /dev $C/dev; mount -t tmpfs tmpfs $C/tmp; chroot $C /rt/rt.sh /rt/$1 $2"
