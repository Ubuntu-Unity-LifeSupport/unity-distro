/* grab-probe - is someone holding an active pointer or keyboard grab?
 *
 * Tries to grab the pointer and the keyboard on the root window and releases
 * them at once. AlreadyGrabbed means another client holds an active grab:
 * with a pointer grab stuck, the pointer still moves but clicks reach only
 * the grabbing client. Prints one line; exit status 1 if either is grabbed.
 *
 * Build: cc -O2 -o grab-probe grab-probe.c -lX11
 */
#include <stdio.h>
#include <X11/Xlib.h>

static const char *
status_name (int status)
{
  switch (status)
    {
    case GrabSuccess:     return "free";
    case AlreadyGrabbed:  return "GRABBED";
    case GrabFrozen:      return "FROZEN";
    case GrabInvalidTime: return "invalid-time";
    case GrabNotViewable: return "not-viewable";
    default:              return "?";
    }
}

int
main (void)
{
  Display *dpy = XOpenDisplay (NULL);
  if (!dpy)
    {
      fprintf (stderr, "grab-probe: cannot open display\n");
      return 2;
    }

  Window root = DefaultRootWindow (dpy);
  int p = XGrabPointer (dpy, root, False, ButtonPressMask, GrabModeAsync,
                        GrabModeAsync, None, None, CurrentTime);
  if (p == GrabSuccess)
    XUngrabPointer (dpy, CurrentTime);

  int k = XGrabKeyboard (dpy, root, False, GrabModeAsync, GrabModeAsync,
                         CurrentTime);
  if (k == GrabSuccess)
    XUngrabKeyboard (dpy, CurrentTime);

  XSync (dpy, False);
  printf ("pointer=%s keyboard=%s\n", status_name (p), status_name (k));
  XCloseDisplay (dpy);

  return (p == AlreadyGrabbed || k == AlreadyGrabbed) ? 1 : 0;
}
