/* shaped-flicker: map and unmap an override-redirect shaped window, its shape
 * alternating between a non-empty and an empty region, like Wine menus do.
 * LP #2165662: compiz dereferences a null shaped shadow pixmap.
 * Build: cc -O2 -o shaped-flicker shaped-flicker.c -lX11 -lXext
 * Usage: shaped-flicker [iterations] */
#include <X11/Xlib.h>
#include <X11/extensions/shape.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
  int n = argc > 1 ? atoi(argv[1]) : 200;
  Display *dpy = XOpenDisplay(NULL);
  if (!dpy) { fprintf(stderr, "no display\n"); return 1; }
  XSetWindowAttributes a = { .override_redirect = True, .background_pixel = 0x808080 };
  Window w = XCreateWindow(dpy, DefaultRootWindow(dpy), 300, 300, 200, 150, 0,
                           CopyFromParent, InputOutput, CopyFromParent,
                           CWOverrideRedirect | CWBackPixel, &a);
  XRectangle full[2] = { { 0, 0, 200, 100 }, { 0, 100, 150, 50 } }; /* not a plain rectangle */
  for (int i = 0; i < n; i++) {
    XShapeCombineRectangles(dpy, w, ShapeBounding, 0, 0, full, 2, ShapeSet, Unsorted);
    XMapWindow(dpy, w); XSync(dpy, False); usleep(30000);
    XUnmapWindow(dpy, w); XSync(dpy, False);
    XShapeCombineRectangles(dpy, w, ShapeBounding, 0, 0, NULL, 0, ShapeSet, Unsorted); /* empty */
    XMapWindow(dpy, w); XSync(dpy, False); usleep(30000);
    XUnmapWindow(dpy, w); XSync(dpy, False);
    if (i % 50 == 0) { printf("iteration %d\n", i); fflush(stdout); }
  }
  printf("done %d\n", n);
  return 0;
}
