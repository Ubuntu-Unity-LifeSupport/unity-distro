// utfconv - call nux's ConvertUTF* the way NUnicode.cpp does and print what
// comes back: result code, how far the pointers moved, and the output.
#include <cstdio>
#include <cstring>
#include <NuxCore/NuxCore.h>

static void utf8_to_32(const char *label, const char *in)
{
  unsigned int out[64];
  memset(out, 0xAB, sizeof out);
  const unsigned char *src = (const unsigned char *)in;
  const unsigned char *src_end = src + strlen(in);
  unsigned int *dst = out;
  nux::ConversionResult r = nux::ConvertUTF8toUTF32(&src, src_end, &dst, out + 64,
                                                    nux::lenientConversion);
  std::printf("%-10s 8->32 result=%d consumed=%td produced=%td first=", label, (int)r,
              src - (const unsigned char *)in, dst - out);
  for (int i = 0; i < 4; i++) std::printf("%08x ", out[i]);
  std::printf("\n");
}

static void utf32_to_8(const char *label, const unsigned int *in, int n)
{
  unsigned char out[64];
  memset(out, 0xAB, sizeof out);
  const unsigned int *src = in;
  unsigned char *dst = out;
  nux::ConversionResult r = nux::ConvertUTF32toUTF8(&src, in + n, &dst, out + 64,
                                                    nux::lenientConversion);
  std::printf("%-10s 32->8 result=%d consumed=%td produced=%td bytes=", label, (int)r,
              src - in, dst - out);
  for (int i = 0; i < 8; i++) std::printf("%02x ", out[i]);
  std::printf("\n");
}

int main()
{
  utf8_to_32("ascii", "Hi");
  utf8_to_32("cyrillic", "\xd0\x9f\xd1\x80");          // "Пр"
  utf8_to_32("invalid", "a\xff" "b");
  const unsigned int pr[] = { 0x41f, 0x440 };
  utf32_to_8("cyrillic", pr, 2);
  return 0;
}
