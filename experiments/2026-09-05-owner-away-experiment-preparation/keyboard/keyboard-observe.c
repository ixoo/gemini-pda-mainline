// SPDX-License-Identifier: GPL-2.0-only
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/kd.h>
#include <linux/vt.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#include "protocol.h"

#define STEP_MS 10000
#define IDLE_MS 2000
#define EVENT_LIMIT 64
#define BYTE_LIMIT 128

static volatile sig_atomic_t interrupted;
static struct termios saved;
static int ttyfd = -1;
static bool changed;

static void on_signal(int signum)
{
	interrupted = signum;
}

static int restore(void)
{
	if (!changed)
		return 0;
	if (tcsetattr(ttyfd, TCSANOW, &saved))
		return -1;
	changed = false;
	return 0;
}

static void cleanup(void)
{
	(void)restore();
}

static long long monotonic_ms(void)
{
	struct timespec now;
	if (clock_gettime(CLOCK_MONOTONIC, &now))
		return -1;
	return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int no_held_keys(int fd)
{
	unsigned char keys[(KEY_MAX + 8) / 8] = { 0 };
	if (ioctl(fd, EVIOCGKEY(sizeof(keys)), keys) < 0)
		return -1;
	for (size_t i = 0; i < sizeof(keys); i++)
		if (keys[i])
			return -1;
	return 0;
}

static int function_strings(void)
{
	/* K_F1..K_F10, K_FIND, K_SELECT, K_PGUP and K_PGDN. */
	const unsigned char indexes[] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
					20, 23, 24, 25 };
	const char *const values[] = { "\033[[A", "\033[[B", "\033[[C",
		"\033[[D", "\033[[E", "\033[17~", "\033[18~", "\033[19~",
		"\033[20~", "\033[21~", "\033[1~", "\033[4~",
		"\033[5~", "\033[6~" };
	for (size_t i = 0; i < sizeof(indexes); i++) {
		struct kbsentry entry = { .kb_func = indexes[i] };
		if (ioctl(ttyfd, KDGKBSENT, &entry) < 0 ||
		    !memchr(entry.kb_string, 0, sizeof(entry.kb_string)) ||
		    strcmp((char *)entry.kb_string, values[i]))
			return -1;
	}
	return 0;
}

static int window(int fd, int duration_ms, bool idle)
{
	long long start = monotonic_ms();
	unsigned int events = 0, bytes = 0;
	if (start < 0)
		return -1;
	for (;;) {
		struct pollfd pollfds[] = { { fd, POLLIN, 0 }, { ttyfd, POLLIN, 0 } };
		long long now = monotonic_ms();
		int ready;
		if (interrupted || now < 0 || ferror(stdout))
			return -1;
		if (now - start >= duration_ms)
			break;
		ready = poll(pollfds, 2, (int)(duration_ms - (now - start)));
		if (ready < 0) {
			if (errno == EINTR)
				continue;
			return -1;
		}
		for (size_t i = 0; i < 2; i++)
			if (pollfds[i].revents & (POLLERR | POLLHUP | POLLNVAL))
				return -1;
		if (pollfds[0].revents & POLLIN) {
			struct input_event event;
			ssize_t n = read(fd, &event, sizeof(event));
			if (n < 0 && (errno == EAGAIN || errno == EINTR))
				continue;
			if (n != (ssize_t)sizeof(event) || idle || ++events > EVENT_LIMIT)
				return -1;
			printf("event type=%u code=%u value=%d\n",
			       event.type, event.code, event.value);
			if (event.type == EV_SYN && event.code == SYN_DROPPED)
				return -1;
		}
		if (pollfds[1].revents & POLLIN) {
			unsigned char data[32];
			ssize_t n = read(ttyfd, data, sizeof(data));
			if (n < 0 && (errno == EAGAIN || errno == EINTR))
				continue;
			if (n <= 0 || idle || bytes + (size_t)n > BYTE_LIMIT)
				return -1;
			bytes += n;
			printf("tty hex=");
			for (ssize_t i = 0; i < n; i++)
				printf("%02x", data[i]);
			putchar('\n');
		}
	}
	if (no_held_keys(fd) || ferror(stdout))
		return -1;
	printf("window events=%u bytes=%u held=0\n", events, bytes);
	return 0;
}

int main(int argc, char **argv)
{
	struct stat info;
	struct termios raw;
	struct vt_stat vt;
	struct sigaction action = { .sa_handler = on_signal };
	char name[128] = { 0 }, path[64], canonical[64];
	unsigned int eventno, expected_major, expected_minor;
	int fd = -1, mode, meta_mode, output_flags, status = 2;
	char extra;

	/* The admitted baseline launcher supplies exact independently observed
	 * sysfs identity and makes tty1 exclusive. This helper never launches a
	 * shell, grabs evdev, changes VT/keymap, or writes a hardware resource. */
	if (argc != 5 || strcmp(argv[1], "--capture") ||
	    sscanf(argv[2], "event%u%c", &eventno, &extra) != 1 ||
	    sscanf(argv[3], "%u%c", &expected_major, &extra) != 1 ||
	    sscanf(argv[4], "%u%c", &expected_minor, &extra) != 1 ||
	    eventno > 255 || expected_major != 13 || expected_minor > 1048575) {
		fprintf(stderr, "usage: keyboard-observe --capture eventN 13 MINOR\n");
		return 2;
	}
	snprintf(canonical, sizeof(canonical), "event%u", eventno);
	if (strcmp(argv[2], canonical) || strcmp(argv[3], "13"))
		return 2;
	snprintf(canonical, sizeof(canonical), "%u", expected_minor);
	if (strcmp(argv[4], canonical))
		return 2;
	setvbuf(stdout, NULL, _IONBF, 0);
	output_flags = fcntl(STDOUT_FILENO, F_GETFL);
	if (output_flags < 0 ||
	    fcntl(STDOUT_FILENO, F_SETFL, output_flags | O_NONBLOCK) < 0)
		return 2;
	printf("keyboard-observe version=1\n");
	snprintf(path, sizeof(path), "/dev/input/event%u", eventno);
	fd = open(path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
	if (fd < 0 || fstat(fd, &info) || !S_ISCHR(info.st_mode) ||
	    major(info.st_rdev) != expected_major ||
	    minor(info.st_rdev) != expected_minor ||
	    ioctl(fd, EVIOCGNAME(sizeof(name) - 1), name) < 0 ||
	    strcmp(name, "keyboard-matrix") || no_held_keys(fd))
		goto finish;
	ttyfd = open("/dev/tty1", O_RDWR | O_NONBLOCK | O_NOFOLLOW | O_NOCTTY | O_CLOEXEC);
	if (ttyfd < 0 || fstat(ttyfd, &info) || !S_ISCHR(info.st_mode) ||
	    major(info.st_rdev) != 4 || minor(info.st_rdev) != 1 ||
	    ioctl(ttyfd, VT_GETSTATE, &vt) || vt.v_active != 1 ||
	    ioctl(ttyfd, KDGKBMODE, &mode) || mode != K_UNICODE ||
	    ioctl(ttyfd, KDGKBMETA, &meta_mode) || meta_mode != K_ESCPREFIX ||
	    function_strings() || tcgetattr(ttyfd, &saved))
		goto finish;
	if (atexit(cleanup))
		goto finish;
	sigemptyset(&action.sa_mask);
	if (sigaction(SIGINT, &action, NULL) || sigaction(SIGTERM, &action, NULL) ||
	    sigaction(SIGHUP, &action, NULL) || sigaction(SIGPIPE, &action, NULL))
		goto finish;
	raw = saved;
	cfmakeraw(&raw);
	raw.c_cc[VMIN] = 0;
	raw.c_cc[VTIME] = 0;
	/* TCSANOW preserves queued input: stale input must refuse, never flush. */
	if (tcsetattr(ttyfd, TCSANOW, &raw))
		goto finish;
	changed = true;
	printf("device event=event%u major=%u minor=%u name=keyboard-matrix\n",
	       eventno, expected_major, expected_minor);
	if (dprintf(ttyfd, "\r\nKeyboard check: release every key. Wait for each step.\r\n") < 0 ||
	    window(fd, IDLE_MS, true))
		goto finish;
	printf("preflight state=pass vt=1 unicode=1 held=0 functions=exact\n");
	for (size_t i = 0; i < sizeof(instructions) / sizeof(instructions[0]); i++) {
		printf("step begin index=%zu\n", i);
		if (dprintf(ttyfd, "\r\n%zu/20 (10 seconds): %s\r\n",
			    i + 1, instructions[i]) < 0 || window(fd, STEP_MS, false))
			goto finish;
		printf("step end index=%zu\n", i);
	}
	if (ioctl(ttyfd, VT_GETSTATE, &vt) || vt.v_active != 1 ||
	    ioctl(ttyfd, KDGKBMODE, &mode) || mode != K_UNICODE ||
	    ioctl(ttyfd, KDGKBMETA, &meta_mode) || meta_mode != K_ESCPREFIX ||
	    function_strings() || restore())
		goto finish;
	if (printf("complete steps=20 restored=1\n") < 0 || ferror(stdout))
		goto finish;
	status = 0;
finish:
	if (restore())
		status = 2;
	if (status)
		printf("incomplete reason=capture-or-preflight restored=%d\n", !changed);
	if (ttyfd >= 0)
		close(ttyfd);
	if (fd >= 0)
		close(fd);
	return status;
}
