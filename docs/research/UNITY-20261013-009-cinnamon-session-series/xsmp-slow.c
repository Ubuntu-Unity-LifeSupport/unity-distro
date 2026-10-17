/*
 * xsmp-slow - a slow but ordinary XSMP client, for UNITY-20260927-014 round 2 (allowed by C, 2026-10-17).
 *
 * Only libSM's public API, in its normal order: SmcOpenConnection; a SaveYourself without shutdown (the one every
 * client gets after registering) is answered at once; when the end-session SaveYourself arrives, wait DELAY seconds, then SmcInteractRequest (the client asks to interact, as an editor with unsaved work does);
 * after HOLD seconds more, SmcCloseConnection. Nothing is built by hand on the wire, and the connection is never
 * broken mid-phase. Every event is printed with a timestamp.
 *
 * Expected: the session manager holds the logout while this client has asked to interact (its inhibitor), also in an
 * inactive session, and the logout goes on once the client has closed its connection.
 *
 *   cc -o xsmp-slow xsmp-slow.c $(pkg-config --cflags --libs sm ice)
 *   ./xsmp-slow DELAY HOLD        (in the session's environment: SESSION_MANAGER set)
 */
#include <X11/ICE/ICElib.h>
#include <X11/SM/SMlib.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double t0;
static int delay_s, hold_s;
static double save_at = -1, close_at = -1;
static SmcConn conn;

static double now(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void say(const char *what)
{
	printf("%8.2f s  %s\n", now() - t0, what);
	fflush(stdout);
}

static void save_yourself(SmcConn c, SmPointer data, int save_type, Bool shutdown, int interact_style, Bool fast)
{
	char buf[160];
	snprintf(buf, sizeof buf, "SaveYourself (save_type %d, shutdown %d, interact_style %d, fast %d)", save_type,
		 shutdown, interact_style, fast);
	say(buf);
	/* The SaveYourself every client gets after registering (no shutdown) is answered at once, as clients do;
	   only the end-session one, which allows interaction, is answered late with an InteractRequest. */
	if (!shutdown || interact_style == SmInteractStyleNone) {
		say("SaveYourselfDone(True)");
		SmcSaveYourselfDone(c, True);
		return;
	}
	if (save_at < 0)
		save_at = now() + delay_s;
}

static void interact(SmcConn c, SmPointer data)
{
	say("Interact granted; InteractDone(cancel=False), SaveYourselfDone(True)");
	SmcInteractDone(c, False);
	SmcSaveYourselfDone(c, True);
}

static void die(SmcConn c, SmPointer data)
{
	say("Die");
	SmcCloseConnection(c, 0, NULL);
	exit(0);
}

static void save_complete(SmcConn c, SmPointer data)
{
	say("SaveComplete");
}

static void shutdown_cancelled(SmcConn c, SmPointer data)
{
	say("ShutdownCancelled");
}

int main(int argc, char **argv)
{
	delay_s = argc > 1 ? atoi(argv[1]) : 3;
	hold_s = argc > 2 ? atoi(argv[2]) : 45;
	t0 = now();

	SmcCallbacks cb = {
		.save_yourself = { save_yourself, NULL },
		.die = { die, NULL },
		.save_complete = { save_complete, NULL },
		.shutdown_cancelled = { shutdown_cancelled, NULL },
	};
	char err[256], *id = NULL;
	conn = SmcOpenConnection(NULL, NULL, SmProtoMajor, SmProtoMinor,
				 SmcSaveYourselfProcMask | SmcDieProcMask | SmcSaveCompleteProcMask |
					 SmcShutdownCancelledProcMask,
				 &cb, NULL, &id, sizeof err, err);
	if (conn == NULL) {
		fprintf(stderr, "SmcOpenConnection: %s\n", err);
		return 2;
	}
	printf("%8.2f s  connected, client id %s\n", now() - t0, id ? id : "(none)");
	fflush(stdout);
	IceConn ice = SmcGetIceConnection(conn);

	for (;;) {
		struct pollfd p = { .fd = IceConnectionNumber(ice), .events = POLLIN };
		if (poll(&p, 1, 200) > 0 && IceProcessMessages(ice, NULL, NULL) != IceProcessMessagesSuccess) {
			say("connection closed by the session manager");
			return 0;
		}
		if (save_at > 0 && now() >= save_at) {
			save_at = 0;
			say("InteractRequest(SmDialogNormal)");
			SmcInteractRequest(conn, SmDialogNormal, interact, NULL);
			close_at = now() + hold_s;
		}
		if (close_at > 0 && now() >= close_at) {
			say("SmcCloseConnection");
			SmcCloseConnection(conn, 0, NULL);
			return 0;
		}
	}
}
