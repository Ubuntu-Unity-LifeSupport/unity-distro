/* t32.c - UNITY-20261013-002: a minimal program to count dynamic loader messages per process and per exec.
 * t32 [N]: prints its pid, whether libgtk-nocsd / libunity-gtk4-menu are mapped, then execs itself with N-1 until
 * N is 0. Built 64-bit and 32-bit (-m32) on the test target. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int mapped(const char *name)
{
	char line[512];
	int n = 0;
	FILE *f = fopen("/proc/self/maps", "r");

	if (f == NULL)
		return -1;
	while (fgets(line, sizeof line, f) != NULL)
		if (strstr(line, name) != NULL)
			n = 1;
	fclose(f);
	return n;
}

int main(int argc, char **argv)
{
	int n = argc > 1 ? atoi(argv[1]) : 0;

	printf("t32 pid %d bits %zu nocsd %d gtk4-menu %d left %d\n", (int)getpid(), sizeof(void *) * 8,
	       mapped("libgtk-nocsd.so.0"), mapped("libunity-gtk4-menu.so.0"), n);
	fflush(stdout);
	if (n > 0) {
		char next[16];
		snprintf(next, sizeof next, "%d", n - 1);
		execl("/proc/self/exe", argv[0], next, (char *)NULL);
		perror("execl");
		return 1;
	}
	return 0;
}
