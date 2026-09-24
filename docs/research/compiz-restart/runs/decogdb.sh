#!/bin/sh
# Follow compiz across a SIGHUP exec and log which branch leaves an inactive
# window's shadow rect empty.
P=$(pgrep -x compiz)
cat > /tmp/deco.gdb <<'G'
set pagination off
set confirm off
set breakpoint pending on
set follow-exec-mode same
handle SIGHUP nostop noprint pass
handle SIGPIPE nostop noprint pass
handle SIGCHLD nostop noprint pass
handle SIGUSR1 nostop noprint pass
handle SIGUSR2 nostop noprint pass
dprintf DecoratedWindow.cpp:605,"NOSHADOW-ELEM impl=%p elements=%d\n", this, (int)this->deco_elements_
dprintf DecoratedWindow.cpp:626,"TEX-MISSING impl=%p active=%d\n", this, (int)this->active.value_
dprintf DecoratedWindow.cpp:872,"REDRAW-UNMAPPED impl=%p\n", this
dprintf DecoratedWindow.cpp:1081,"UDP impl=%p\n", impl_.get()
continue
G
sudo -n timeout 60 gdb -q -batch -p $P -x /tmp/deco.gdb > /var/tmp/cz/deco.txt 2>&1 &
sleep 6
kill -HUP $P
sleep 50
wait
