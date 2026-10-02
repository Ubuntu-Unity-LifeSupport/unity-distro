// fullscreen-direct - UNITY-20260927-027. Reach CreateOpenGLWindow's
// fullscreen branch through the public API, with one window creation only,
// then destroy the display. The branch XFree()s m_X11VideoModes after the mode
// switch and ~GraphicsDisplay XFree()s it again. Needs an X server with
// XFree86-VidModeExtension and a mode of exactly WIDTH x HEIGHT.
// Usage: fullscreen-direct WIDTH HEIGHT
#include <cstdio>
#include <cstdlib>
#include <NuxCore/NuxCore.h>
#include <NuxGraphics/NuxGraphics.h>
#include <NuxGraphics/GLWindowManager.h>
#include <NuxGraphics/GraphicsDisplay.h>

int main(int argc, char **argv)
{
  setvbuf(stdout, nullptr, _IONBF, 0);
  int w = argc > 2 ? std::atoi(argv[1]) : 1280;
  int h = argc > 2 ? std::atoi(argv[2]) : 800;
  nux::NuxCoreInitialize(0);
  nux::NuxGraphicsInitialize();
  nux::GraphicsDisplay *gd = nux::GetGraphicsDisplay();
  std::printf("display before: %p\n", (void *) gd);
  gd = gGLWindowManager.CreateGLWindow("fullscreen-direct", w, h,
                                       nux::WINDOWSTYLE_NORMAL, 0,
                                       true /* fullscreen */, false);
  // Whether the fullscreen branch ran is seen from outside: a uprobe on
  // XF86VidModeSwitchToMode (fullscreen-trace.bt).
  std::printf("CreateGLWindow(%d x %d, fullscreen) -> %p\n", w, h, (void *) gd);
  delete gd;
  std::printf("DELETED\n");
  return 0;
}
