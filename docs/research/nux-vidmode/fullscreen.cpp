// fullscreen - recreate the Nux window fullscreen at the server's own mode,
// then tear down. Before the fix the mode list is freed twice: once after the
// mode switch in CreateOpenGLWindow, again in ~GraphicsDisplay.
#include <cstdio>
#include <memory>
#include <Nux/Nux.h>
#include <Nux/WindowThread.h>
#include <NuxGraphics/GraphicsDisplay.h>

int main()
{
  nux::NuxInitialize(0);
  std::unique_ptr<nux::WindowThread> wt(
    nux::CreateGUIThread("fullscreen", 300, 200, 0, nullptr, nullptr));
  nux::GraphicsDisplay *gd = nux::GetGraphicsDisplay();
  bool ok = gd && gd->CreateOpenGLWindow("fullscreen", 1280, 800,
                                          nux::WINDOWSTYLE_NORMAL, nullptr,
                                          true, false);
  std::printf("FULLSCREEN %s\n", ok ? "CREATED" : "FAILED");
  wt.reset();
  std::printf("TORN DOWN\n");
  return 0;
}
