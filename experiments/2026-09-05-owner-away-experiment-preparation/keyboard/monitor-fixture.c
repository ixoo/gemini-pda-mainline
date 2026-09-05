/* SPDX-License-Identifier: MIT */
/* Host-only entry: built-in harmless child, no exec or device helper path. */
#define MONITOR_FIXTURE
#include "monitor.c"
#include <limits.h>
#include <stdlib.h>
#ifndef FIXTURE_ROOT
#error "An explicit managed fixture root is required"
#endif
static const char *mode;
static void pause_ms(int n) { (void)poll(NULL, 0, n); }
static void fixture_child(void)
{
	char line[64], b[4096];
	if (!strcmp(mode, "ignore") || !strcmp(mode, "late-signal")) signal(SIGTERM, SIG_IGN);
	/* The harness deliberately passes fd 47. Neither it nor stdin may leak. */
	if (fcntl(47, F_GETFD) >= 0 || read(0, b, 1) != 0) _exit(124);
	int n = snprintf(line, sizeof(line), "fixture-child=%ld\n", (long)getpid());
	if (store(1, line, (size_t)n)) _exit(123);
	if (!strcmp(mode, "disconnect")) {
		for (;;) {
			if (store(1, "fixture-progress\n", sizeof("fixture-progress\n") - 1)) _exit(122);
			pause_ms(20);
		}
	}
#ifdef MONITOR_FULL_DURATION
	/* One harmless run witnesses the observation boundary then forced cleanup. */
	if (!strcmp(mode, "ignore")) {
		pause_ms(202000);
		(void)store(1, "fixture-observation-boundary=202000\n", sizeof("fixture-observation-boundary=202000\n") - 1);
	}
#endif
	if (!strcmp(mode, "nonzero")) _exit(7);
	if (!strcmp(mode, "close-live")) { close(1); close(2); }
	if (!strcmp(mode, "fill") || !strcmp(mode, "stderr") || !strcmp(mode, "limit")) {
		memset(b, 'x', sizeof(b));
		int fd = !strcmp(mode, "stderr") ? 2 : 1;
		int blocks = !strcmp(mode, "limit") ? 64 : 20;
		for (int i = 0; i < blocks; ++i) if (store(fd, b, sizeof(b))) _exit(122);
	}
	if (!strcmp(mode, "normal") || !strcmp(mode, "late") || !strcmp(mode, "late-default")) {
		pause_ms(20); (void)store(1, "fixture-done\n", 13); _exit(0);
	}
	for (;;) pause();
}
static void fixture_after_status(void)
{
	if (!strcmp(mode, "late")) raise(SIGHUP);
}
static void fixture_after_defaults(void)
{
	if (!strcmp(mode, "late-default")) raise(SIGHUP);
}
static void fixture_before_term(void)
{
	if (!strcmp(mode, "late-signal")) pause_ms(40);
}
int main(int argc, char **argv)
{
	const char *modes[] = { "normal", "late", "late-default", "late-signal", "disconnect", "nonzero", "close-live", "ignore", "wait", "fill", "stderr", "limit" };
	char resolved[PATH_MAX];
	bool admitted = false;
	if (argc != 3 || !realpath(argv[1], resolved) || strcmp(argv[1], resolved) ||
	    strncmp(resolved, FIXTURE_ROOT "/", sizeof(FIXTURE_ROOT))) return 2;
	for (size_t i = 0; i < sizeof(modes) / sizeof(modes[0]); ++i)
		if (!strcmp(argv[2], modes[i])) admitted = true;
	if (!admitted) return 2;
	mode = argv[2];
	int dir = open(resolved, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
	struct stat s;
	if (dir < 0 || fstat(dir, &s) || s.st_uid != getuid() || (s.st_mode & 0777) != 0700) return 2;
	if (!strcmp(mode, "disconnect")) {
		char text[32]; int n = snprintf(text, sizeof(text), "%ld\n", (long)getpid());
		int fd = exclusive(dir, "monitor.pid");
		if (fd < 0 || store(fd, text, (size_t)n) || fsync(fd)) return 2;
		close(fd);
	}
	int result = keyboard_monitor_run(dir, "event0", "64");
	if (!strcmp(mode, "disconnect")) {
		char text[16]; int n = snprintf(text, sizeof(text), "%d\n", result);
		int fd = exclusive(dir, "monitor.exit");
		if (fd < 0 || store(fd, text, (size_t)n) || fsync(fd)) return 2;
		close(fd);
	}
	close(dir);
	return result;
}
