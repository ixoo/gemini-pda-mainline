// SPDX-License-Identifier: MIT
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/kd.h>
#include <linux/tiocl.h>
#include <linux/tty.h>
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

/* Diagnostic snapshot only: no reads, prompts, termios changes or setters.
 * GETSHIFTSTATE is transient and excludes the VT's lock/slock state. */
static int report_state(int fd)
{
	unsigned char keys[(KEY_MAX + 8) / 8] = { 0 };
	unsigned char shift = TIOCL_GETSHIFTSTATE, after = TIOCL_GETSHIFTSTATE;
	unsigned char leds;
	int meta;

	if (ioctl(fd, EVIOCGKEY(sizeof(keys)), keys) < 0 ||
	    ioctl(ttyfd, TIOCLINUX, &shift) ||
	    ioctl(ttyfd, KDGKBLED, &leds) || ioctl(ttyfd, KDGKBMETA, &meta))
		return 2;
	printf("console-state version=1 shift=%u leds=%u meta=%d held=", shift, leds, meta);
	for (unsigned int key = 0; key <= KEY_MAX; key++)
		if (keys[key / 8] & (1U << (key % 8)))
			printf("%u,", key);
	putchar('\n');
	for (unsigned int table = 0; table < 16; table++) {
		struct kbentry entry = { .kb_table = table, .kb_index = KEY_SPACE };
		if (ioctl(ttyfd, KDGKBENT, &entry))
			return 2;
		printf("space table=%u value=%u\n", table, entry.kb_value);
	}
	if (ioctl(ttyfd, TIOCLINUX, &after))
		return 2;
	return printf("console-state complete=1 shift_after=%u\n", after) < 0 || ferror(stdout) ? 2 : 0;
}

/* Preserve queued bytes rather than flushing them. Every read is nonblocking. */
static int drain_console(void)
{
	struct pollfd pending = { ttyfd, POLLIN, 0 };
	int discipline, ready;
	unsigned int total = 0;

	/* A closed VT can retain flip-buffer input with no ldisc consumer.
	 * In the pinned kernel, reselecting the current N_TTY takes the no-op
	 * branch but restarts that worker. It neither replaces nor flushes the
	 * discipline. Preserve the released bytes instead of using TCIFLUSH.
	 */
	if (ioctl(ttyfd, TIOCGETD, &discipline) || discipline != N_TTY ||
	    ioctl(ttyfd, TIOCSETD, &discipline)) {
		printf("console-drain requeue=refused\n");
		return 2;
	}
	printf("console-drain requeue=accepted ldisc=0\n");
	ready = poll(&pending, 1, 1000);
	if (ready < 0 || interrupted ||
	    (pending.revents & (POLLERR | POLLHUP | POLLNVAL)))
		return 2;
	for (unsigned int i = 0; i < 128 && !interrupted; i++) {
		unsigned char data[32];
		ssize_t count = read(ttyfd, data, sizeof(data));
		if (!count || (count < 0 && errno == EAGAIN)) {
			printf("console-drain empty=1 bytes=%u\n", total);
			return ferror(stdout) ? 2 : 0;
		}
		if (count < 0)
			return 2;
		total += count;
		printf("console-drain bytes=%ld hex=", (long)count);
		for (ssize_t j = 0; j < count; j++)
			printf("%02x", data[j]);
		putchar('\n');
		if (ferror(stdout))
			return 2;
	}
	printf("console-drain empty=unproven bytes=%u limit=4096\n", total);
	return 2;
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
	const char *reason = "setup";
	struct input_event last_event = { 0 };
	ssize_t last_read = -1;
	int last_byte = -1, read_errno = 0;
	unsigned char failed_bytes[32];
	size_t failed_count = 0, pending_count = 0;
	struct input_event pending[8];
	ssize_t pending_read = -1;
	int pending_errno = 0;
	long long start, reported, quiet = -1;
	bool state_only = argc == 4 && !strcmp(argv[1], "--state");
	bool drain_only = argc == 4 && !strcmp(argv[1], "--drain-console");

	if (state_only || drain_only) {
		argc--;
		argv++;
	}

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
	    strcmp(name, "keyboard-matrix") || (!state_only && released(fd)))
		goto done;
	ttyfd = open("/dev/tty1", O_RDWR | O_NONBLOCK | O_NOFOLLOW | O_NOCTTY | O_CLOEXEC);
	if (ttyfd < 0 || fstat(ttyfd, &info) || !S_ISCHR(info.st_mode) ||
	    major(info.st_rdev) != 4 || minor(info.st_rdev) != 1 ||
	    ioctl(ttyfd, VT_GETSTATE, &vt) || vt.v_active != 1 ||
	    ioctl(ttyfd, KDGKBMODE, &mode) || mode != K_UNICODE)
		goto done;
	if (state_only) {
		result = report_state(fd);
		goto done;
	}
	if (tcgetattr(ttyfd, &saved) || atexit(cleanup))
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
	if (drain_only) {
		setvbuf(stdout, NULL, _IONBF, 0);
		result = drain_console();
		if (released(fd))
			result = 2;
		goto done;
	}
	/* Release and preserve input left while the VT was closed. Keep this
	 * same descriptor open through readiness so the backlog cannot recur
	 * between this preparation and the owner's Space press.
	 */
	setvbuf(stdout, NULL, _IONBF, 0);
	reason = "preflight";
	if (drain_console() || released(fd))
		goto done;
	if (printf("space-ready=preflight-complete\n") < 0)
		goto done;
	/* Refuse new input arriving during preparation, before readiness. */
	struct pollfd fds[] = { { fd, POLLIN, 0 }, { ttyfd, POLLIN, 0 } };
	if (poll(fds, 2, 0) != 0 ||
	    dprintf(ttyfd, "\r\nPress and release SPACE to begin the keyboard test.\r\n"
		    "Then leave all keys released until the first prompt.\r\n"
		    "This screen waits up to five minutes.\r\n") < 0)
		goto done;
	start = now_ms();
	reported = start;
	if (start < 0)
		goto done;
	while (!interrupted) {
		long long now = now_ms();
		if (now < 0 || now - start >= WAIT_MS) {
			reason = "deadline-or-clock";
			goto done;
		}
		if (now - reported >= WAIT_REPORT_MS) {
			if (printf("space-ready=waiting\n") < 0)
				goto done;
			reported = now;
		}
		int ready = poll(fds, 2, 100);
		if (ready < 0 && errno == EINTR)
			continue;
		if (ready < 0 || ((fds[0].revents | fds[1].revents) &
		    (POLLERR | POLLHUP | POLLNVAL))) {
			reason = "poll";
			goto done;
		}
		if (ready)
			quiet = -1;
		if (fds[0].revents & POLLIN) {
			last_read = read(fd, &last_event, sizeof(last_event));
			read_errno = last_read < 0 ? errno : 0;
			if (last_read != (ssize_t)sizeof(last_event)) {
				reason = "event-read";
				goto done;
			}
			if (++events > 512 || edge(&last_event, &state)) {
				reason = "event-sequence";
				goto done;
			}
		}
		if (fds[1].revents & POLLIN) {
			unsigned char data[32];
			ssize_t n = read(ttyfd, data, sizeof(data));
			if (n <= 0 || bytes + n > 128) {
				last_read = n;
				read_errno = n < 0 ? errno : 0;
				reason = "console-read";
				goto done;
			}
			for (ssize_t i = 0; i < n; i++)
				if (data[i] != ' ') {
					last_byte = data[i];
					memcpy(failed_bytes, data, n);
					failed_count = n;
					reason = "console-byte";
					goto done;
				}
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
	if (interrupted)
		reason = "signal";
	if (restore()) {
		reason = "restore";
		result = 2;
	}
	if (ttyfd >= 0) {
		if (!state_only && !drain_only && dprintf(ttyfd, result ? "\r\nStart cancelled. Test has not begun.\r\n" :
			    "\r\nReady. Keep keys released; prompts will start shortly.\r\n") < 0)
			result = 2;
		close(ttyfd);
	}
	/* On the observed console mismatch, retain the entire read and up to
	 * eight already queued evdev records. Never wait, retry or admit a start. */
	if (fd >= 0 && failed_count) {
		while (pending_count < sizeof(pending) / sizeof(pending[0])) {
			pending_read = read(fd, &pending[pending_count], sizeof(pending[0]));
			pending_errno = pending_read < 0 ? errno : 0;
			if (pending_read != (ssize_t)sizeof(pending[0]))
				break;
			pending_count++;
		}
	}
	if (fd >= 0)
		close(fd);
	if (state_only)
		return result;
	if (drain_only) {
		printf("console-drain complete=%d restored=%d\n", !result, !changed);
		return result;
	}
	if (result)
		printf("space-ready=failed reason=%s restored=%d state=%d events=%u bytes=%u "
		       "read=%ld type=%u code=%u value=%d console_byte=%d errno=%d\n",
		       reason, !changed, state, events, bytes, (long)last_read,
		       last_event.type, last_event.code, last_event.value, last_byte, read_errno);
	if (failed_count) {
		printf("console-read bytes=%zu hex=", failed_count);
		for (size_t i = 0; i < failed_count; i++)
			printf("%02x", failed_bytes[i]);
		putchar('\n');
		for (size_t i = 0; i < pending_count; i++)
			printf("pending type=%u code=%u value=%d\n",
			       pending[i].type, pending[i].code, pending[i].value);
		printf("pending count=%zu limit=8 read=%ld errno=%d\n",
		       pending_count, (long)pending_read, pending_errno);
	}
	if (!result && printf("space-ready=passed released=1 restored=1\n") < 0)
		result = 2;
	return result;
}
