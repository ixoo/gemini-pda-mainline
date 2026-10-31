// SPDX-License-Identifier: MIT
/*
 * Lid and brightness policy for the station. On SW_LID closed: inhibit the
 * keyboard input device, power the backlight down and blank the console; on
 * open, undo all three. Nothing is done until the lid has been seen open
 * once, so a misread or floating lid input at boot cannot lock the console
 * out. Each transition is logged to the kernel log. Fn+B and Fn+N (Fn is
 * KEY_LEFTMETA) step the backlight down and up, autorepeat included; the
 * console keymap gives those two keys no Fn action. The backlight also
 * follows the console's own blanking (setterm --blank), which the simple
 * framebuffer cannot do itself: it is powered down while the console is
 * blanked, checked once a second. init respawns this program.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/tiocl.h>
#include <poll.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define LID_NAME "gpio-keys"
#define KEYBOARD_NAME "keyboard-matrix"
#define BL_POWER "/sys/class/backlight/backlight/bl_power"
#define BL_BRIGHTNESS "/sys/class/backlight/backlight/brightness"
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

/* The console number the kernel has blanked, 0 if none. */
static int console_blanked(void)
{
	char arg = TIOCL_BLANKEDSCREEN;
	int fd = open(CONSOLE, O_RDWR | O_CLOEXEC);
	int ret;

	if (fd < 0)
		return 0;
	ret = ioctl(fd, TIOCLINUX, &arg);
	close(fd);
	return ret > 0 ? ret : 0;
}

static int backlight_off = -1;

static int set_backlight(int off)
{
	int ret = 0;

	if (off != backlight_off) {
		ret = put(BL_POWER, off ? "4" : "0");
		if (!ret)
			backlight_off = off;
	}
	return ret;
}

static void apply(const char *keyboard, int closed)
{
	char inhibited[600];
	int k, b, c;

	snprintf(inhibited, sizeof(inhibited), "%s/inhibited", keyboard);
	k = put(inhibited, closed ? "1" : "0");
	c = blank(closed);
	b = set_backlight(closed);
	say("lid %s: keyboard_inhibit=%d backlight=%d console_blank=%d\n",
	    closed ? "closed" : "open", k, b, c);
}

/* Brightness steps, never fully dark; the backlight has levels 0 to 1023. */
static const int steps[] = { 16, 32, 64, 96, 128, 192, 256, 384, 512, 640, 768, 1023 };
#define STEPS (int)(sizeof(steps) / sizeof(steps[0]))

static void step_brightness(int up)
{
	char text[16];
	int fd, n, level = -1, i;

	fd = open(BL_BRIGHTNESS, O_RDONLY | O_CLOEXEC);
	if (fd >= 0) {
		n = read(fd, text, sizeof(text) - 1);
		if (n > 0) {
			text[n] = 0;
			sscanf(text, "%d", &level);
		}
		close(fd);
	}
	if (level < 0)
		return;
	/* The next step strictly above or below the current level. */
	for (i = up ? 0 : STEPS - 1; i >= 0 && i < STEPS; i += up ? 1 : -1)
		if (up ? steps[i] > level : steps[i] < level)
			break;
	if (i < 0 || i >= STEPS)
		return;
	snprintf(text, sizeof(text), "%d", steps[i]);
	put(BL_BRIGHTNESS, text);
}

int main(void)
{
	char lid[512], keyboard[512];
	unsigned long sw[(SW_MAX + 8 * sizeof(long)) / (8 * sizeof(long))] = { 0 };
	struct input_event ev;
	struct pollfd fds[2];
	int fd, kfd, closed, armed, fn = 0;

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
	kfd = open_events(keyboard);
	if (kfd < 0)
		say("no keyboard events; brightness keys off\n");
	fds[0] = (struct pollfd){ .fd = fd, .events = POLLIN };
	fds[1] = (struct pollfd){ .fd = kfd, .events = POLLIN };
	while (poll(fds, kfd < 0 ? 1 : 2, 1000) >= 0) {
		int blanked = console_blanked();

		if (!(armed && closed) && !!blanked != backlight_off)
			say("console %s: backlight=%d\n", blanked ? "blanked" : "unblanked",
			    set_backlight(!!blanked));
		if ((fds[1].revents & POLLIN) && read(kfd, &ev, sizeof(ev)) == sizeof(ev) &&
		    ev.type == EV_KEY) {
			if (ev.code == KEY_LEFTMETA)
				fn = ev.value != 0;
			else if (fn && ev.value && (ev.code == KEY_B || ev.code == KEY_N))
				step_brightness(ev.code == KEY_N);
		}
		if (!(fds[0].revents & POLLIN))
			continue;
		if (read(fd, &ev, sizeof(ev)) != sizeof(ev))
			break;
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
