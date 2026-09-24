#!/bin/sh
# Follow compiz across a SIGHUP exec: shadow texture builds, option changes,
# and what each window's generic shadow computation finds.
P=$(pgrep -x compiz)
cat > /tmp/deco4.gdb <<'G'
set pagination off
set confirm off
set breakpoint pending on
set follow-exec-mode same
handle SIGHUP nostop noprint pass
handle SIGPIPE nostop noprint pass
handle SIGCHLD nostop noprint pass
handle SIGUSR1 nostop noprint pass
handle SIGUSR2 nostop noprint pass
dprintf DecorationsManager.cpp:68,"BUILD radius=%u\n", radius
dprintf DecorationsManager.cpp:95,"OPTCHANGED active=%d\n", (int)active
dprintf DecoratedWindow.cpp:633,"GENERIC xid=%lu tex=%p\n", this->win_->priv->id, texture
dprintf DecoratedWindow.cpp:127,"UPDATE xid=%lu old=%u new=%u\n", this->win_->priv->id, old_elements, this->deco_elements_
continue
G
sudo -n timeout 120 gdb -q -batch -p $P -x /tmp/deco4.gdb > /var/tmp/cz/deco4.txt 2>&1 &
sleep 6
kill -HUP $P
sleep 110
wait
