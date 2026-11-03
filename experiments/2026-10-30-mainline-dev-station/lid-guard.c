// SPDX-License-Identifier: MIT
/*
 * Brightness policy for the station. The kernel owns turning the display off: the
 * gemini-lid module on the lid, and the panel's backlight link on any blank. This
 * program is only comfort, and nothing goes wrong without it. Fn+B and Fn+N (Fn is
 * KEY_LEFTMETA) step the backlight down and up, autorepeat included; the console
 * keymap gives those two keys no Fn action. The backlight fades down over the last
 * seconds before the kernel's idle deadline and back up on waking. init respawns
 * this program.
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
#include <time.h>
#include <unistd.h>

#define LID_NAME "gpio-keys"
#define KEYBOARD_NAME "keyboard-matrix"
#define BL_BRIGHTNESS "/sys/class/backlight/backlight/brightness"
#define BL_POWER "/sys/class/backlight/backlight/bl_power"
#define CONSOLE "/dev/tty1"
#define BLANK_SECONDS "/sys/module/kernel/parameters/consoleblank"
/* The fades: long enough to see, short enough not to hold a wake back. */
#define DIM_LEVEL 16
#define FADE_DOWN_STEPS 40
#define FADE_DOWN_MS 75
/* It ends as the kernel blanks, with no time held at the dim level. */
#define FADE_DOWN_LEAD_MS (FADE_DOWN_STEPS * FADE_DOWN_MS)
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
	/* No controlling tty: this program must not take tty1 from the shell. */
	int fd = open(CONSOLE, O_RDWR | O_CLOEXEC | O_NOCTTY);
	int ret;

	if (fd < 0)
		return 0;
	ret = ioctl(fd, TIOCLINUX, &arg);
	close(fd);
	return ret > 0 ? ret : 0;
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

static long long now_ms(void)
{
	struct timespec t;

	clock_gettime(CLOCK_REALTIME, &t);
	return t.tv_sec * 1000LL + t.tv_nsec / 1000000;
}

/* When the kernel saw the event, in the same clock as now_ms(). */
static long long event_ms(const struct input_event *ev)
{
	return ev->time.tv_sec * 1000LL + ev->time.tv_usec / 1000;
}

static void set_brightness(int level)
{
	char text[16];

	snprintf(text, sizeof(text), "%d", level);
	put(BL_BRIGHTNESS, text);
}

/*
 * Step from one level to another, slowly at the dark end, where the eye sees most.
 * With fds, returns early and non-zero on any input. Without, input waits for the end.
 */
static int fade(int from, int to, int steps, int ms, struct pollfd *fds, int nfds)
{
	int low = from < to ? from : to, high = from < to ? to : from, i;

	for (i = 1; i <= steps; i++) {
		int done = from < to ? i : steps - i;

		set_brightness(low + (high - low) * done * done / (steps * steps));
		if (poll(fds, fds ? nfds : 0, ms) > 0)
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
	int fd, kfd, closed, fn = 0, nfds, restore = -1, quick = 0, was_blanked = 0, wait = 1000;
	long long last_input = now_ms();

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
	while (poll(fds, nfds, quick > 0 ? 50 : wait) >= 0) {
		int blanked = console_blanked();

		if (quick > 0)
			quick--;
		wait = 1000;
		if (!!blanked != was_blanked) {
			say("console %s\n", blanked ? "blanked" : "unblanked");
			was_blanked = !!blanked;
			/*
			 * The kernel is lighting it again at the dim level, a moment after it
			 * reports unblanked; then back up to the owner's. The key that woke it
			 * must not cancel this, so it waits, like any other input.
			 */
			if (!blanked && restore >= 0) {
				int i;

				for (i = 0; i < 20 && read_number(BL_POWER) != 0; i++)
					poll(NULL, 0, 25);
				fade(DIM_LEVEL, restore, FADE_UP_STEPS, FADE_UP_MS, NULL, 0);
				restore = -1;
			}
		}
		if (!closed && !blanked) {
			int seconds = read_number(BLANK_SECONDS);
			/* Only input resets the kernel's deadline; console output does not. */
			long long start = last_input + seconds * 1000LL - FADE_DOWN_LEAD_MS;
			long long left = start - now_ms();

			if (seconds * 1000 > FADE_DOWN_LEAD_MS && restore < 0 && left <= 0) {
				int level = read_number(BL_BRIGHTNESS);

				if (level > DIM_LEVEL) {
					restore = level;
					if (fade(level, DIM_LEVEL, FADE_DOWN_STEPS, FADE_DOWN_MS,
						 fds, nfds)) {
						set_brightness(restore);
						restore = -1;
					}
				}
			} else if (restore >= 0 && (seconds * 1000 <= FADE_DOWN_LEAD_MS || left > 0)) {
				/* The deadline moved or went, with no blank after all. */
				set_brightness(restore);
				restore = -1;
			} else if (seconds * 1000 > FADE_DOWN_LEAD_MS && left > 0 && left < wait) {
				/* Wake exactly when the fade has to start. */
				wait = left;
			}
		}
		if ((fds[1].revents & POLLIN) && read(kfd, &ev, sizeof(ev)) == sizeof(ev) &&
		    ev.type == EV_KEY) {
			last_input = event_ms(&ev);
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
		if (restore >= 0) {
			set_brightness(restore);
			restore = -1;
		}
		last_input = event_ms(&ev);
	}
	say("lid event stream ended\n");
	return 1;
}
