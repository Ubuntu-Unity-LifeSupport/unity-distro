/* shaped-stale (UNITY-20260927-002, agent A): does compiz keep drawing a
 * shadow for a shaped window after its shape became empty?
 * Phases, each announced on stdout and held for HOLD seconds so a screenshot
 * can be taken: 0 nothing mapped; 1 an override-redirect window at 300,300
 * mapped with a non-rectangular shape; 2 the same window, still mapped, its
 * shape set to the empty region; 3 unmapped again.
 * Build: cc -O2 -o shaped-stale shaped-stale.c -lX11 -lXext
 * Usage: shaped-stale [HOLD] */
#include <X11/Xlib.h>
#include <X11/extensions/shape.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static void phase(int n, const char *what, int hold)
{
  printf("phase %d: %s\n", n, what);
  fflush(stdout);
  sleep(hold);
}

int main(int argc, char **argv)
{
  int hold = argc > 1 ? atoi(argv[1]) : 4;
  Display *dpy = XOpenDisplay(NULL);
  if (!dpy) { fprintf(stderr, "no display\n"); return 1; }
  XSetWindowAttributes a = { .override_redirect = True, .background_pixel = 0x808080 };
  Window w = XCreateWindow(dpy, DefaultRootWindow(dpy), 300, 300, 200, 150, 0,
                           CopyFromParent, InputOutput, CopyFromParent,
                           CWOverrideRedirect | CWBackPixel, &a);
  XRectangle full[2] = { { 0, 0, 200, 100 }, { 0, 100, 150, 50 } };
  phase(0, "nothing mapped", hold);
  XShapeCombineRectangles(dpy, w, ShapeBounding, 0, 0, full, 2, ShapeSet, Unsorted);
  XMapWindow(dpy, w); XSync(dpy, False);
  phase(1, "mapped, shaped", hold);
  XShapeCombineRectangles(dpy, w, ShapeBounding, 0, 0, NULL, 0, ShapeSet, Unsorted);
  XSync(dpy, False);
  phase(2, "mapped, empty shape", hold);
  XUnmapWindow(dpy, w); XSync(dpy, False);
  phase(3, "unmapped", hold);
  return 0;
}
