#!/bin/sh
# Backtrace of the first g_return_if_fail warnings compiz prints on SIGHUP.
P=$(pgrep -x compiz)
sudo -n timeout 300 gdb -q -batch -p $P \
  -iex "set debuginfod enabled off" \
  -ex "handle SIGHUP nostop noprint pass" \
  -ex "handle SIGSEGV stop print" \
  -ex "break g_return_if_fail_warning" \
  -ex "continue" -ex "bt 20" \
  -ex "continue" -ex "bt 20" \
  -ex "detach" > /var/tmp/cz/hashbt.txt 2>&1 &
sleep 8
kill -HUP $P
wait
