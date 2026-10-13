/* dummy.c - UNITY-20261013-002: a stand-in 32-bit "libgtk-nocsd.so.0" that only reports where the dynamic loader
 * found it, to show what $LIB expands to for 32-bit processes. Installed on the test target only, then removed. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>

__attribute__((constructor)) static void where(void)
{
	Dl_info info;

	if (dladdr((void *)where, &info) && info.dli_fname != NULL)
		fprintf(stderr, "dummy preload loaded from %s\n", info.dli_fname);
}
