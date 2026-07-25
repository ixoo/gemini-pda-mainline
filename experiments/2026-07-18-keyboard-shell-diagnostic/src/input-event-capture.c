// SPDX-License-Identifier: GPL-2.0-only
#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>

#define CAPTURE_SECONDS 60
#define MAX_EVENTS 64

static bool keyboard_name(const char *name)
{
	return strcasestr(name, "keyboard") != NULL ||
	       strcasestr(name, "matrix") != NULL;
}

static int open_keyboard(char *path, size_t path_size, char *name,
			 size_t name_size)
{
	int event;

	for (event = 0; event < MAX_EVENTS; event++) {
		int fd;

		if (snprintf(path, path_size, "/dev/input/event%d", event) >=
		    (int)path_size)
			continue;
		fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
		if (fd < 0)
			continue;
		memset(name, 0, name_size);
		if (ioctl(fd, EVIOCGNAME(name_size - 1), name) >= 0 &&
		    keyboard_name(name))
			return fd;
		close(fd);
	}
	errno = ENODEV;
	return -1;
}

static const char *event_type(unsigned short type)
{
	switch (type) {
	case EV_SYN:
		return "EV_SYN";
	case EV_KEY:
		return "EV_KEY";
	case EV_MSC:
		return "EV_MSC";
	default:
		return "OTHER";
	}
}

int main(void)
{
	struct timespec started;
	char path[64];
	char name[256];
	int fd;

	fd = open_keyboard(path, sizeof(path), name, sizeof(name));
	if (fd < 0) {
		printf("input-capture device=absent duration=%ds error=%s\n",
		       CAPTURE_SECONDS, strerror(errno));
		return 0;
	}
	printf("input-capture device=%s name=%s duration=%ds grab=no\n",
	       path, name, CAPTURE_SECONDS);
	fflush(stdout);
	if (clock_gettime(CLOCK_MONOTONIC, &started) != 0) {
		perror("clock_gettime");
		close(fd);
		return 1;
	}

	for (;;) {
		struct input_event events[16];
		struct timespec now;
		struct pollfd pfd = { .fd = fd, .events = POLLIN };
		ssize_t length;
		int timeout_ms;
		int ready;

		if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
			break;
		timeout_ms = (CAPTURE_SECONDS - (int)(now.tv_sec - started.tv_sec)) *
			     1000;
		if (timeout_ms <= 0)
			break;
		ready = poll(&pfd, 1, timeout_ms);
		if (ready == 0)
			break;
		if (ready < 0) {
			if (errno == EINTR)
				continue;
			perror("poll");
			break;
		}
		length = read(fd, events, sizeof(events));
		if (length < 0) {
			if (errno == EAGAIN || errno == EINTR)
				continue;
			perror("read");
			break;
		}
		for (size_t index = 0;
		     index < (size_t)length / sizeof(events[0]); index++) {
			const struct input_event *event = &events[index];

			if (event->type != EV_SYN && event->type != EV_KEY &&
			    !(event->type == EV_MSC && event->code == MSC_SCAN))
				continue;
			printf("input-event type=%s(%u) code=%u value=%d\n",
			       event_type(event->type), event->type, event->code,
			       event->value);
		}
		fflush(stdout);
	}
	printf("input-capture complete duration=%ds\n", CAPTURE_SECONDS);
	close(fd);
	return 0;
}
