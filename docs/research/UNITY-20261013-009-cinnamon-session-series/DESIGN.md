# cinnamon-session 6.4.2-1+unity8: design for the Design Challenger (round 1)

Base: the published 6.4.2-1+unity7 (7393f0e). One commit per change, minimal diff, comments only on new code where
needed. The measurements are in README.md and logs/.

## 1. UNITY-20260927-014: a no-confirmation logout of an inactive session waits for a dialog nobody sees

**Measured (logs/07, logs/10).**
1. The session is switched away: `dm-tool switch-to-greeter`; mike's logind session is `Active=no`, the greeter is on
   seat0.
2. `org.gnome.SessionManager.Logout(1)` (no confirmation) is called.
3. compiz, an XSMP client, does not answer QueryEndSession. `_on_query_end_session_timeout` adds a "Not responding"
   inhibitor for it, so `end_session_or_report_inhibitors` asks for a dialog: the shell's times out after 25 s, then
   the GTK fallback is launched on the inactive display. The session stays in QUERY_END_SESSION indefinitely.
4. Our +unity2 patch ("ask for a dialog when inhibitors have nobody to be shown to") only makes sure a dialog is
   asked for. Here the dialog exists but nobody can see it.

In every foreground run compiz answers, and the logout ends within about 1 s. Why compiz goes silent off-VT is a
separate task (UNITY-20261017-002, compiz) and is not addressed here.

**Change.** In `_on_query_end_session_timeout`, when all of these hold:
- the logout mode is `CSM_MANAGER_LOGOUT_MODE_NO_CONFIRMATION`;
- the session is not active (`g_object_get (manager->priv->system, "active", &active, NULL)`, the property our
  SessionIsActive export already binds);

then a client that did not reply gets no "Not responding" inhibitor, exactly as already happens for
`CSM_MANAGER_LOGOUT_MODE_FORCE`. The loop's existing `g_warning` stays, so the log still names the client.
Inhibitors that applications registered themselves are not touched: if there are any, the dialog path is unchanged.

**What it must not do (C's condition).**
- It must not drop a client that would have asked to save. The change applies only to a client that **never replied**
  to QueryEndSession within the timeout. A client that wants to save or interact answers the query (SaveYourself
  with interact, or an interact request) and is not in `query_clients` when the timer fires.
- It applies only to an inactive session with no confirmation requested. In a foreground session, or with confirmation
  requested, behaviour is unchanged (UNITY-20260929-007's foreground path keeps its "Not responding" dialog).

**Alternatives weighed.**
- (b) Fix compiz: that is the root of compiz's silence, but it is a different package, and any other client that goes
  silent off-VT would hang the same way. It stays as UNITY-20261017-002.
- Applying it to every no-confirmation logout, active or not: that would remove the foreground "Not responding" choice,
  which is the designed behaviour (gnome-session has it too). Rejected.
- Upstream: master af94f9b has the same timeout code (sweep), so nothing to take from there.

**Tests.**
- target2, the same `switch` run (logs/10): the session ends within the timeout plus a few seconds, and the log shows
  the "failed to reply" warning and no dialog launch.
- Regression:
  - a foreground `stopped` run (at-spi2-registryd stopped) still waits with its "Not responding" inhibitor;
  - an ordinary foreground logout still takes about 1 s;
  - the UNITY-20260928-019 logout/shutdown cycle.

## 2. UNITY-20261013-009: the "disconnected" handler is connected twice per XSMP client

**Measured (logs/02).** `on_client_disconnected` and `_disconnect_client` run twice for the same client pointer, for
an xterm that exits normally and for one killed with SIGKILL.

**Cause.** Two connections of the same handler:
- `on_store_client_added` connects "disconnected" for every client added to the store;
- `on_xsmp_client_register_request` connects it again when an XSMP client registers. (This is csm-manager.c, with
  `g_signal_connect (client, "disconnected", G_CALLBACK (on_client_disconnected), manager)` in both places.)

**Change.** Remove the second connection, in `on_xsmp_client_register_request`. Every client still gets exactly one
connection, through the store. (XSMP clients are added to the store in `accept_xsmp_connection` before they can
register.)

**Effects of the double call today, removed by the change.**
- `_disconnect_client` runs twice: the restart and app logic twice, and inhibitor removal twice;
- `csm_store_remove` of an id already removed;
- in the end-session phase, `end_phase` may run twice for the last client.

**Tests.** The same bpftrace counts: one `on_client_disconnected` and one `_disconnect_client` per client, for an
xterm exit and a SIGKILL. An ordinary logout is unchanged.

## 3. UNITY-20261013-010: watch_id is not zeroed when the IO watch returns FALSE

**Not reproduced.** In both close paths the client is finalized while its own watch callback is still dispatching,
so `watch_id` still names a live source and `g_source_remove` finds it. A stale id would matter only on the
`IceProcessMessagesConnectionClosed` path if the client outlived the callback, and no trace showed that.

**Change (defensive, one line, no comment).** In `client_iochannel_watch`, set `client->priv->watch_id = 0` before
returning FALSE, so `csm_xsmp_client_disconnect` never removes a source that GLib has already destroyed. C leans to
bundling it into +unity8 if the DC agrees; otherwise the task closes NOT_REPRODUCED.

## 4. UNITY-20261013-011: the SmsConn of a client refused while stopping is not freed (one line for the DC)

`accept_xsmp_connection` returns FALSE while the session is stopping, and libSM does not free the SmsConn it
allocated (`_SmsProtocolSetupProc`). Freeing it would mean calling `SmsCleanUp` from inside libSM's own setup
callback, which also shuts the protocol down on that IceConn. That is riskier than a one-time leak in a process that
is about to exit. **Proposal: won't fix (NOT_APPLICABLE)**, unless the DC sees a safe form.
