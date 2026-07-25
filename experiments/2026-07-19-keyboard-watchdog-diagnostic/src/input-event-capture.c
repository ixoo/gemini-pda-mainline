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

#define CAPTURE_SECONDS 15
#define EVENT_PATH_PREFIX "/dev/input/event"

static bool keyboard_name(const char *name)
{
	return strcasestr(name, "keyboard") != NULL ||
	       strcasestr(name, "matrix") != NULL;
}

static bool safe_name(const char *name)
{
	const unsigned char *cursor = (const unsigned char *)name;

	if (!*cursor)
		return false;
	for (; *cursor; cursor++) {
		if (*cursor < 0x20 || *cursor == 0x7f)
			return false;
	}
	return true;
}

static bool event_path(const char *path)
{
	const char *suffix;

	if (strncmp(path, EVENT_PATH_PREFIX, strlen(EVENT_PATH_PREFIX)) != 0)
		return false;
	suffix = path + strlen(EVENT_PATH_PREFIX);
	if (!*suffix)
		return false;
	for (; *suffix; suffix++) {
		if (*suffix < '0' || *suffix > '9')
			return false;
	}
	return true;
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

int main(int argc, char **argv)
{
	struct timespec deadline;
	char actual_name[256] = { 0 };
	const char *expected_name;
	const char *path;
	int fd;

	if (argc != 3) {
		fprintf(stderr,
			"usage: input-event-capture /dev/input/eventN EXPECTED_NAME\n");
		return 2;
	}
	/* Keep the safety bound machine-auditable in the static binary. */
	printf("input-capture policy=capture-bound-15s-absolute-monotonic\n");
	path = argv[1];
	expected_name = argv[2];
	if (!event_path(path) || !safe_name(expected_name) ||
	    !keyboard_name(expected_name)) {
		fprintf(stderr,
			"input-capture requested_device=%s state=rejected reason=invalid-request\n",
			path);
		return 2;
	}

	fd = open(path, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
	if (fd < 0) {
		printf("input-capture requested_device=%s state=unavailable duration=%ds error=%s\n",
		       path, CAPTURE_SECONDS, strerror(errno));
		return 0;
	}
	if (ioctl(fd, EVIOCGNAME(sizeof(actual_name) - 1), actual_name) < 0) {
		printf("input-capture requested_device=%s state=rejected duration=%ds reason=name-query-failed error=%s\n",
		       path, CAPTURE_SECONDS, strerror(errno));
		close(fd);
		return 0;
	}
	if (!safe_name(actual_name) || strcmp(actual_name, expected_name) != 0 ||
	    !keyboard_name(actual_name)) {
		printf("input-capture requested_device=%s state=rejected duration=%ds reason=identity-changed\n",
		       path, CAPTURE_SECONDS);
		close(fd);
		return 0;
	}

	printf("input-capture device=%s name=%s identity=exact-sysfs-to-fd duration=%ds grab=no\n",
	       path, actual_name, CAPTURE_SECONDS);
	fflush(stdout);
	if (clock_gettime(CLOCK_MONOTONIC, &deadline) != 0) {
		perror("clock_gettime");
		close(fd);
		return 1;
	}
	deadline.tv_sec += CAPTURE_SECONDS;

	for (;;) {
		struct input_event events[16];
		struct timespec now;
		struct pollfd pfd = { .fd = fd, .events = POLLIN };
		ssize_t length;
		long remaining_nsec;
		long remaining_sec;
		int timeout_ms;
		int ready;

		if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
			break;
		remaining_sec = deadline.tv_sec - now.tv_sec;
		remaining_nsec = deadline.tv_nsec - now.tv_nsec;
		if (remaining_nsec < 0) {
			remaining_sec--;
			remaining_nsec += 1000000000L;
		}
		if (remaining_sec < 0 ||
		    (remaining_sec == 0 && remaining_nsec <= 0))
			break;
		/* Round down so poll cannot extend beyond the absolute deadline. */
		timeout_ms = (int)(remaining_sec * 1000L +
				   remaining_nsec / 1000000L);
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
		if (length % (ssize_t)sizeof(events[0]) != 0) {
			printf("input-capture state=failed reason=partial-event-record\n");
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
