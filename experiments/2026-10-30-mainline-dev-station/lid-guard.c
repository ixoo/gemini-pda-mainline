// SPDX-License-Identifier: MIT
/*
 * Lid policy for the station. On SW_LID closed: inhibit the keyboard input
 * device, power the backlight down and blank the console; on open, undo all
 * three. Nothing is done until the lid has been seen open once, so a misread
 * or floating lid input at boot cannot lock the console out. Each transition
 * is logged to the kernel log. init respawns this program.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/tiocl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define LID_NAME "gpio-keys"
#define KEYBOARD_NAME "keyboard-matrix"
#define BL_POWER "/sys/class/backlight/backlight/bl_power"
#define CONSOLE "/dev/tty1"

static void say(const char *fmt, ...)
{
	char line[256];
	va_list ap;
	int fd, n;

	n = snprintf(line, sizeof(line), "lid-guard: ");
	va_start(ap, fmt);
	vsnprintf(line + n, sizeof(line) - n, fmt, ap);
	va_end(ap);
	fd = open("/dev/kmsg", O_WRONLY | O_CLOEXEC);
	if (fd >= 0) {
		/* The kernel log is the only place to report to. */
		(void)!write(fd, line, strlen(line));
		close(fd);
	}
}

/* The input class directory (input0...) whose name matches. */
static int find_input(const char *name, char *dir, size_t size)
{
	struct dirent *e;
	DIR *d = opendir("/sys/class/input");
	char path[512], got[128];
	int found = 0;

	if (!d)
		return 0;
	while (!found && (e = readdir(d))) {
		FILE *f;

		if (strncmp(e->d_name, "input", 5))
			continue;
		snprintf(path, sizeof(path), "/sys/class/input/%s/name", e->d_name);
		f = fopen(path, "r");
		if (!f)
			continue;
		if (fgets(got, sizeof(got), f)) {
			got[strcspn(got, "\n")] = 0;
			if (!strcmp(got, name)) {
				snprintf(dir, size, "/sys/class/input/%s", e->d_name);
				found = 1;
			}
		}
		fclose(f);
	}
	closedir(d);
	return found;
}

/* The /dev/input/eventN node under an input class directory. */
static int open_events(const char *dir)
{
	struct dirent *e;
	DIR *d = opendir(dir);
	char path[512];
	int fd = -1;

	if (!d)
		return -1;
	while (fd < 0 && (e = readdir(d)))
		if (!strncmp(e->d_name, "event", 5)) {
			snprintf(path, sizeof(path), "/dev/input/%s", e->d_name);
			fd = open(path, O_RDONLY | O_CLOEXEC);
		}
	closedir(d);
	return fd;
}

static int put(const char *path, const char *value)
{
	int fd = open(path, O_WRONLY | O_CLOEXEC);
	int ok;

	if (fd < 0)
		return -errno;
	ok = write(fd, value, strlen(value)) == (ssize_t)strlen(value);
	close(fd);
	return ok ? 0 : -EIO;
}

static int blank(int on)
{
	char arg = on ? TIOCL_BLANKSCREEN : TIOCL_UNBLANKSCREEN;
	int fd = open(CONSOLE, O_RDWR | O_CLOEXEC);
	int ret;

	if (fd < 0)
		return -errno;
	ret = ioctl(fd, TIOCLINUX, &arg) ? -errno : 0;
	close(fd);
	return ret;
}

static void apply(const char *keyboard, int closed)
{
	char inhibited[600];
	int k, b, c;

	snprintf(inhibited, sizeof(inhibited), "%s/inhibited", keyboard);
	k = put(inhibited, closed ? "1" : "0");
	b = put(BL_POWER, closed ? "4" : "0");
	c = blank(closed);
	say("lid %s: keyboard_inhibit=%d backlight=%d console_blank=%d\n",
	    closed ? "closed" : "open", k, b, c);
}

int main(void)
{
	char lid[512], keyboard[512];
	unsigned long sw[(SW_MAX + 8 * sizeof(long)) / (8 * sizeof(long))] = { 0 };
	struct input_event ev;
	int fd, closed, armed;

	if (!find_input(LID_NAME, lid, sizeof(lid)) ||
	    !find_input(KEYBOARD_NAME, keyboard, sizeof(keyboard))) {
		say("no lid or keyboard input device\n");
		sleep(60);
		return 1;
	}
	fd = open_events(lid);
	if (fd < 0 || ioctl(fd, EVIOCGSW(sizeof(sw)), sw) < 0) {
		say("cannot read the lid switch\n");
		sleep(60);
		return 1;
	}
	closed = !!(sw[SW_LID / (8 * sizeof(long))] & (1UL << (SW_LID % (8 * sizeof(long)))));
	armed = !closed;
	say("start: lid %s, %s\n", closed ? "closed" : "open",
	    armed ? "armed" : "waiting for the lid to open");
	if (armed)
		apply(keyboard, 0);
	while (read(fd, &ev, sizeof(ev)) == sizeof(ev)) {
		if (ev.type != EV_SW || ev.code != SW_LID)
			continue;
		closed = !!ev.value;
		if (!armed && !closed) {
			armed = 1;
			say("armed\n");
		}
		if (armed)
			apply(keyboard, closed);
	}
	say("lid event stream ended\n");
	return 1;
}
