// SPDX-License-Identifier: MIT
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

#ifndef WAIT_MS
#define WAIT_MS 300000
#endif
#ifndef WAIT_REPORT_MS
#define WAIT_REPORT_MS 20000
#endif
static volatile sig_atomic_t interrupted;
static struct termios saved;
static int ttyfd = -1;
static bool changed;

static void on_signal(int signal_number)
{
	interrupted = signal_number;
}

static int restore(void)
{
	if (changed && tcsetattr(ttyfd, TCSANOW, &saved))
		return -1;
	changed = false;
	return 0;
}

static void cleanup(void)
{
	(void)restore();
}

static long long now_ms(void)
{
	struct timespec now;
	if (clock_gettime(CLOCK_MONOTONIC, &now))
		return -1;
	return (long long)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int released(int fd)
{
	unsigned char keys[(KEY_MAX + 8) / 8] = { 0 };
	if (ioctl(fd, EVIOCGKEY(sizeof(keys)), keys) < 0)
		return -1;
	for (size_t i = 0; i < sizeof(keys); i++)
		if (keys[i])
			return -1;
	return 0;
}

/* Require one Space press/release; never accept a different key or lost events. */
static int edge(const struct input_event *event, int *state)
{
	if (event->type == EV_MSC && event->code == MSC_SCAN)
		return 0;
	if (event->type == EV_SYN && event->code == SYN_REPORT)
		return 0;
	if (event->type != EV_KEY || event->code != KEY_SPACE)
		return -1;
	if (*state == 0 && event->value == 1)
		*state = 1;
	else if (*state == 1 && event->value == 0)
		*state = 2;
	else if (*state != 1 || event->value != 2)
		return -1;
	return 0;
}

int main(int argc, char **argv)
{
	struct stat info;
	struct termios raw;
	struct vt_stat vt;
	struct sigaction action = { .sa_handler = on_signal };
	char path[64], name[128] = { 0 }, extra;
	unsigned int eventno, minorno, events = 0, bytes = 0;
	int fd = -1, mode, state = 0, result = 2;
	long long start, reported, quiet = -1;

	if (argc != 3 || sscanf(argv[1], "event%u%c", &eventno, &extra) != 1 ||
	    eventno > 255 || sscanf(argv[2], "%u%c", &minorno, &extra) != 1 ||
	    minorno > 1048575)
		return 2;
	snprintf(path, sizeof(path), "event%u", eventno);
	if (strcmp(path, argv[1]))
		return 2;
	snprintf(path, sizeof(path), "%u", minorno);
	if (strcmp(path, argv[2]))
		return 2;
	snprintf(path, sizeof(path), "/dev/input/event%u", eventno);
	fd = open(path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
	if (fd < 0 || fstat(fd, &info) || !S_ISCHR(info.st_mode) ||
	    major(info.st_rdev) != 13 || minor(info.st_rdev) != minorno ||
	    ioctl(fd, EVIOCGNAME(sizeof(name) - 1), name) < 0 ||
	    strcmp(name, "keyboard-matrix") || released(fd))
		goto done;
	ttyfd = open("/dev/tty1", O_RDWR | O_NONBLOCK | O_NOFOLLOW | O_NOCTTY | O_CLOEXEC);
	if (ttyfd < 0 || fstat(ttyfd, &info) || !S_ISCHR(info.st_mode) ||
	    major(info.st_rdev) != 4 || minor(info.st_rdev) != 1 ||
	    ioctl(ttyfd, VT_GETSTATE, &vt) || vt.v_active != 1 ||
	    ioctl(ttyfd, KDGKBMODE, &mode) || mode != K_UNICODE ||
	    tcgetattr(ttyfd, &saved) || atexit(cleanup))
		goto done;
	sigemptyset(&action.sa_mask);
	if (sigaction(SIGINT, &action, NULL) || sigaction(SIGTERM, &action, NULL) ||
	    sigaction(SIGHUP, &action, NULL) || sigaction(SIGPIPE, &action, NULL))
		goto done;
	raw = saved;
	cfmakeraw(&raw);
	raw.c_cc[VMIN] = 0;
	raw.c_cc[VTIME] = 0;
	if (tcsetattr(ttyfd, TCSANOW, &raw))
		goto done;
	changed = true;
	/* Refuse stale input without discarding it before displaying readiness. */
	struct pollfd fds[] = { { fd, POLLIN, 0 }, { ttyfd, POLLIN, 0 } };
	if (poll(fds, 2, 0) != 0 ||
	    dprintf(ttyfd, "\r\nPress and release SPACE to begin the keyboard test.\r\n"
		    "Then leave all keys released until the first prompt.\r\n"
		    "This screen waits up to five minutes.\r\n") < 0)
		goto done;
	setvbuf(stdout, NULL, _IONBF, 0);
	start = now_ms();
	reported = start;
	if (start < 0)
		goto done;
	while (!interrupted) {
		long long now = now_ms();
		if (now < 0 || now - start >= WAIT_MS)
			goto done;
		if (now - reported >= WAIT_REPORT_MS) {
			if (printf("space-ready=waiting\n") < 0)
				goto done;
			reported = now;
		}
		int ready = poll(fds, 2, 100);
		if (ready < 0 && errno == EINTR)
			continue;
		if (ready < 0 || ((fds[0].revents | fds[1].revents) &
		    (POLLERR | POLLHUP | POLLNVAL)))
			goto done;
		if (ready)
			quiet = -1;
		if (fds[0].revents & POLLIN) {
			struct input_event event;
			if (read(fd, &event, sizeof(event)) != (ssize_t)sizeof(event) ||
			    ++events > 512 || edge(&event, &state))
				goto done;
		}
		if (fds[1].revents & POLLIN) {
			unsigned char data[32];
			ssize_t n = read(ttyfd, data, sizeof(data));
			if (n <= 0 || bytes + n > 128)
				goto done;
			for (ssize_t i = 0; i < n; i++)
				if (data[i] != ' ')
					goto done;
			bytes += n;
		}
		if (!ready && state == 2 && bytes && !released(fd)) {
			if (quiet < 0)
				quiet = now;
			if (now - quiet >= 500) {
				result = 0;
				break;
			}
		}
	}
 done:
	if (restore())
		result = 2;
	if (ttyfd >= 0) {
		if (dprintf(ttyfd, result ? "\r\nStart cancelled. Test has not begun.\r\n" :
			    "\r\nReady. Keep keys released; prompts will start shortly.\r\n") < 0)
			result = 2;
		close(ttyfd);
	}
	if (fd >= 0)
		close(fd);
	if (!result && printf("space-ready=passed released=1 restored=1\n") < 0)
		result = 2;
	return result;
}
