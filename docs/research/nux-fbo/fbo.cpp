// fbo - exercise IOpenGLFrameBufferObject's colour attachments the way
// Unity's rendering does (LP: #2160298). FormatFrameBufferObject() empties the
// attachment vectors, so every later attachment write indexes an empty
// std::vector: silent in a normal build, an assertion with
// -D_GLIBCXX_ASSERTIONS. Also checks that destroying the FBO releases the
// texture it held (the emptied vector's destructor never sees the element).
#include <cstdio>
#include <memory>
#include <Nux/Nux.h>
#include <Nux/WindowThread.h>
#include <NuxGraphics/GraphicsDisplay.h>
#include <NuxGraphics/GpuDevice.h>
#include <NuxGraphics/IOpenGLFrameBufferObject.h>

int main()
{
  setvbuf(stdout, nullptr, _IONBF, 0);
  nux::NuxInitialize(0);
  std::unique_ptr<nux::WindowThread> wt(
    nux::CreateGUIThread("fbo", 300, 200, 0, nullptr, nullptr));
  if (!wt) { std::printf("WINDOW NOT CREATED\n"); return 2; }

  nux::GpuDevice *gpu = wt->GetGraphicsDisplay().GetGpuDevice();
  std::printf("max fbo attachments: %d\n", gpu->GetGpuInfo().GetMaxFboAttachment());

  nux::ObjectPtr<nux::IOpenGLBaseTexture> tex =
    gpu->CreateSystemCapableDeviceTexture(64, 64, 1, nux::BITFMT_R8G8B8A8, NUX_TRACKER_LOCATION);
  std::printf("texture created: %s\n", tex.IsValid() ? "yes" : "NO");
  if (!tex.IsValid()) {
    tex = gpu->CreateTexture(64, 64, 1, nux::BITFMT_R8G8B8A8, NUX_TRACKER_LOCATION);
    std::printf("IOpenGLTexture2D created: %s\n", tex.IsValid() ? "yes" : "NO");
    if (!tex.IsValid()) return 3;
  }
  int before = tex->GetReferenceCount();
  {
    nux::ObjectPtr<nux::IOpenGLFrameBufferObject> fbo = gpu->CreateFrameBufferObject();
    fbo->FormatFrameBufferObject(64, 64, nux::BITFMT_R8G8B8A8);
    fbo->SetTextureAttachment(0, tex, 0);
    fbo->Activate();
    std::printf("attachment 0 is our texture: %s\n",
                fbo->TextureAttachment(0) == tex ? "yes" : "no");
    std::printf("texture refs while attached: %d\n", tex->GetReferenceCount());
    fbo->Deactivate();
    std::printf("FBO refs before it goes out of scope: %d (1 = only ours)\n",
                fbo->GetReferenceCount());
  }
  int after = tex->GetReferenceCount();
  std::printf("texture refs before %d, after the FBO is gone %d -> %s\n",
              before, after, after == before ? "released" : "LEAKED");
  std::printf("FBO-TEST DONE\n");
  return after == before ? 0 : 1;
}
