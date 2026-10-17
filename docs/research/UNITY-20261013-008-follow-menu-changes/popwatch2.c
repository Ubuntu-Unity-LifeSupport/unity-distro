/*
 * popwatch2 PID SECONDS - on target2: every 20 ms for SECONDS, the menu popups the process PID (unity-panel-service)
 * shows, one timestamped line per change: each viewable override-redirect top-level window of PID larger than 10x10,
 * as "x,y WxH", in stacking order. The holder's menu and an open submenu are separate windows, so a submenu that
 * collapses shows as its window going away. (popwatch.sh counts windows through xdotool, and its count does not
 * change when a submenu opens or closes.)
 *
 *   cc -o popwatch2 popwatch2.c -lX11
 */
#include <X11/Xatom.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

static int ignore(Display *d, XErrorEvent *e)
{
	return 0;
}

static long pid_of(Display *d, Window w, Atom net_wm_pid)
{
	Atom type;
	int format;
	unsigned long n, after;
	unsigned char *data = NULL;
	long pid = -1;

	if (XGetWindowProperty(d, w, net_wm_pid, 0, 1, False, XA_CARDINAL, &type, &format, &n, &after,
			       &data) == Success && data != NULL) {
		if (n == 1)
			pid = *(long *)data;
		XFree(data);
	}
	return pid;
}

int main(int argc, char **argv)
{
	if (argc < 3)
		return 2;
	long pid = atol(argv[1]);
	int seconds = atoi(argv[2]);
	Display *d = XOpenDisplay(NULL);
	if (d == NULL)
		return 1;
	XSetErrorHandler(ignore);
	Atom net_wm_pid = XInternAtom(d, "_NET_WM_PID", False);
	char last[4096] = "-", cur[4096];
	time_t end = time(NULL) + seconds;

	while (time(NULL) < end) {
		Window root, parent, *children = NULL;
		unsigned int n = 0;
		cur[0] = 0;
		XQueryTree(d, DefaultRootWindow(d), &root, &parent, &children, &n);
		for (unsigned int i = 0; i < n; i++) {
			XWindowAttributes a;
			if (!XGetWindowAttributes(d, children[i], &a))
				continue;
			if (a.map_state != IsViewable || !a.override_redirect || a.width <= 10 || a.height <= 10)
				continue;
			if (pid_of(d, children[i], net_wm_pid) != pid)
				continue;
			char one[64];
			snprintf(one, sizeof one, "%d,%d %dx%d;", a.x, a.y, a.width, a.height);
			strncat(cur, one, sizeof cur - strlen(cur) - 1);
		}
		if (children != NULL)
			XFree(children);
		if (strcmp(cur, last) != 0) {
			struct timeval tv;
			gettimeofday(&tv, NULL);
			struct tm tm;
			gmtime_r(&tv.tv_sec, &tm);
			printf("%02d:%02d:%02d.%03ld popups: %s\n", tm.tm_hour, tm.tm_min, tm.tm_sec,
			       (long)tv.tv_usec / 1000, cur);
			fflush(stdout);
			strcpy(last, cur);
		}
		usleep(20000);
	}
	return 0;
}
