// vidmode - create one Nux window the way Unity's tests and Standalone* tools
// do, and say whether it worked. Segfaults in CreateOpenGLWindow on an X
// server without XFree86-VidModeExtension (Xvfb) before nux is fixed.
#include <cstdio>
#include <memory>
#include <Nux/Nux.h>
#include <Nux/WindowThread.h>

int main()
{
  nux::NuxInitialize(0);
  std::unique_ptr<nux::WindowThread> wt(
    nux::CreateGUIThread("vidmode", 300, 200, 0, nullptr, nullptr));
  std::printf("WINDOW %s\n", wt ? "CREATED" : "NOT CREATED");
  return wt ? 0 : 1;
}
