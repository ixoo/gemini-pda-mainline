// SPDX-License-Identifier: MIT
/*
 * Brightness policy for the station. The lid itself is the kernel's
 * gemini-lid module: backlight off and keyboard ignored while it is closed.
 * This program blanks the console while the lid is closed, which turns the
 * display off under the native pipeline, and otherwise leaves the backlight to
 * the module then. Fn+B and Fn+N (Fn is KEY_LEFTMETA) step the backlight down and
 * up, autorepeat included; the console keymap gives those two keys no Fn action.
 * The backlight also follows the console's own blanking (setterm --blank): it
 * fades down over the last seconds before the kernel's idle deadline, is powered
 * down while the console is blanked, checked once a second, and fades back up on
 * waking. init respawns this program.
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
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define LID_NAME "gpio-keys"
#define KEYBOARD_NAME "keyboard-matrix"
#define BL_POWER "/sys/class/backlight/backlight/bl_power"
#define BL_BRIGHTNESS "/sys/class/backlight/backlight/brightness"
#define CONSOLE "/dev/tty1"
#define BLANK_SECONDS "/sys/module/kernel/parameters/consoleblank"
/* The fades: long enough to see, short enough not to hold a wake back. */
#define DIM_LEVEL 16
#define FADE_DOWN_SECONDS 3
#define FADE_DOWN_STEPS 40
#define FADE_DOWN_MS 75
#define FADE_UP_STEPS 16
#define FADE_UP_MS 30

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

static void console_tiocl(char arg)
{
	int fd = open(CONSOLE, O_RDWR | O_CLOEXEC);

	if (fd < 0)
		return;
	if (ioctl(fd, TIOCLINUX, &arg) < 0)
		say("console request %d failed: %d\n", arg, errno);
	close(fd);
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

/* Brightness steps, never fully dark; the backlight has levels 0 to 1023. */
static const int steps[] = { 16, 32, 64, 96, 128, 192, 256, 384, 512, 640, 768, 1023 };
#define STEPS (int)(sizeof(steps) / sizeof(steps[0]))

static int read_number(const char *path)
{
	char text[16];
	int fd, n, value = -1;

	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd >= 0) {
		n = read(fd, text, sizeof(text) - 1);
		if (n > 0) {
			text[n] = 0;
			sscanf(text, "%d", &value);
		}
		close(fd);
	}
	return value;
}

static void set_brightness(int level)
{
	char text[16];

	snprintf(text, sizeof(text), "%d", level);
	put(BL_BRIGHTNESS, text);
}

/*
 * Step from one level to another, slowly at the dark end, where the eye sees most.
 * Returns early, and non-zero, on any input.
 */
static int fade(int from, int to, int steps, int ms, struct pollfd *fds, int nfds)
{
	int low = from < to ? from : to, high = from < to ? to : from, i;

	for (i = 1; i <= steps; i++) {
		int done = from < to ? i : steps - i;

		set_brightness(low + (high - low) * done * done / (steps * steps));
		if (poll(fds, nfds, ms) > 0)
			return 1;
	}
	return 0;
}

static void step_brightness(int up)
{
	char text[16];
	int level = read_number(BL_BRIGHTNESS), i;

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
	int fd, kfd, closed, fn = 0, nfds, restore = -1, quick = 0;
	time_t last_input = time(NULL);

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
	say("start: lid %s\n", closed ? "closed" : "open");
	kfd = open_events(keyboard);
	if (kfd < 0)
		say("no keyboard events; brightness keys off\n");
	fds[0] = (struct pollfd){ .fd = fd, .events = POLLIN };
	fds[1] = (struct pollfd){ .fd = kfd, .events = POLLIN };
	nfds = kfd < 0 ? 1 : 2;
	/* After a key, look again soon: the kernel wakes the console just after it. */
	while (poll(fds, nfds, quick > 0 ? 50 : 1000) >= 0) {
		int blanked = console_blanked();

		if (quick > 0)
			quick--;
		if (!closed && !!blanked != backlight_off) {
			int level = restore >= 0 ? restore : read_number(BL_BRIGHTNESS);

			if (!blanked && level >= 0) {
				/* Awake: from dark, up to the owner's level. */
				set_brightness(DIM_LEVEL < level ? DIM_LEVEL : level);
				say("console unblanked: backlight=%d\n", set_backlight(0));
				if (fade(DIM_LEVEL < level ? DIM_LEVEL : level, level, FADE_UP_STEPS,
					 FADE_UP_MS, fds, nfds))
					set_brightness(level);
				restore = -1;
			} else {
				say("console %s: backlight=%d\n", blanked ? "blanked" : "unblanked",
				    set_backlight(!!blanked));
			}
		}
		if (!closed && !blanked && backlight_off == 0) {
			int seconds = read_number(BLANK_SECONDS);
			time_t now = time(NULL), active = last_input;
			struct stat st;

			if (!stat(CONSOLE, &st) && st.st_mtime > active)
				active = st.st_mtime;
			if (seconds > FADE_DOWN_SECONDS && restore < 0 &&
			    now - active >= seconds - FADE_DOWN_SECONDS) {
				int level = read_number(BL_BRIGHTNESS);

				if (level > DIM_LEVEL) {
					restore = level;
					if (fade(level, DIM_LEVEL, FADE_DOWN_STEPS, FADE_DOWN_MS,
						 fds, nfds)) {
						set_brightness(restore);
						restore = -1;
					}
				}
			} else if (restore >= 0 && now - active < seconds - FADE_DOWN_SECONDS) {
				/* Output moved the deadline, with no blank after all. */
				set_brightness(restore);
				restore = -1;
			}
		}
		if ((fds[1].revents & POLLIN) && read(kfd, &ev, sizeof(ev)) == sizeof(ev) &&
		    ev.type == EV_KEY) {
			last_input = time(NULL);
			quick = 20;
			if (restore >= 0 && !blanked) {
				set_brightness(restore);
				restore = -1;
			}
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
		/* gemini-lid powered the backlight on or off with the lid. */
		backlight_off = closed;
		if (restore >= 0) {
			set_brightness(restore);
			restore = -1;
		}
		last_input = time(NULL);
		/* The display goes with it, and no console output wakes it. */
		console_tiocl(closed ? TIOCL_BLANKSCREEN : TIOCL_UNBLANKSCREEN);
	}
	say("lid event stream ended\n");
	return 1;
}
