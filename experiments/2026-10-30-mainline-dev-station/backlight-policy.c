// SPDX-License-Identifier: MIT
/*
 * Brightness policy for the station. The kernel owns turning the display off: the
 * gemini-lid module on the lid, and the panel's backlight link on any blank. This
 * program is only comfort, and nothing goes wrong without it. Fn+B and Fn+N (Fn is
 * KEY_LEFTMETA) step the backlight down and up, autorepeat included; the console
 * keymap gives those two keys no Fn action. The backlight fades down over the last
 * seconds before the kernel's idle deadline and back up on waking. init respawns
 * this program. It sleeps until input or the fade's start. The kernel doesn't announce
 * a blank or unblank, so it looks only when one is due: for a while after input, and
 * from the fade's start until the blank. An input device it doesn't watch, such as a
 * Bluetooth keyboard, can wake the console without it noticing until the next watched
 * event. Whatever sets the blank timeout must send SIGUSR1, since that also restarts the
 * kernel's deadline and nothing else would wake this program for it.
 *
 * It also darkens the caps lock LED while the screen is dark: lid closed, console
 * blanked, or the backlight off at the end of the fade. Back on, the LED's trigger
 * is set again, which takes the real caps lock state. Without the LED driver the
 * writes fail and are tried again on the next wake. With the lid closed or the
 * console blanked it also takes CPUs 1-9 offline, and brings them back after.
 * When the lid closes and "deep" is on offer (the SPM sleep module is loaded),
 * it suspends to memory, again after each timer wake while the lid stays closed.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <linux/tiocl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define LID_NAME "gpio-keys"
#define KEYBOARD_NAME "keyboard-matrix"
#define PMIC_KEYS_NAME "mtk-pmic-keys"
#define BL_BRIGHTNESS "/sys/class/backlight/backlight/brightness"
#define BL_POWER "/sys/class/backlight/backlight/bl_power"
#define CONSOLE "/dev/tty1"
#define BLANK_SECONDS "/sys/module/kernel/parameters/consoleblank"
#define CAPS_LED_TRIGGER "/sys/class/leds/red:indicator-7/trigger"
#define MEM_SLEEP "/sys/power/mem_sleep"
#define POWER_STATE "/sys/power/state"
/* A suspend that returns sooner than this was woken at once: don't loop on it. */
#define SUSPEND_MIN_MS 2000
/* The fades: long enough to see, short enough not to hold a wake back. */
#define DIM_LEVEL 16
#define FADE_DOWN_STEPS 40
#define FADE_DOWN_MS 75
/* It starts this long before the earliest the kernel can blank. */
#define FADE_DOWN_LEAD_MS (FADE_DOWN_STEPS * FADE_DOWN_MS)
#define FADE_UP_STEPS 16
#define FADE_UP_MS 30
/* Past the deadline by this much with no blank, input we can't see must have moved it. */
#define BLANK_OVERDUE_MS 5000

static void say(const char *fmt, ...)
{
	char line[256];
	va_list ap;
	int fd, n;

	n = snprintf(line, sizeof(line), "backlight-policy: ");
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
	ssize_t n;
	int ret;

	if (fd < 0)
		return -errno;
	n = write(fd, value, strlen(value));
	ret = n < 0 ? -errno : n == (ssize_t)strlen(value) ? 0 : -EIO;
	close(fd);
	return ret;
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

/* Back from a fade that no blank has followed. */
static void undim(int level)
{
	set_brightness(level);
	put(BL_POWER, "0");
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

/* 1 dark, 0 following caps lock, -1 not yet written. */
static int caps_led_dark = -1;

static void caps_led(int dark)
{
	int err;

	if (dark == caps_led_dark)
		return;
	if (dark)
		err = put(CAPS_LED_TRIGGER, "none");
	/* The keypad's trigger follows a compositor too; an older kernel has only the console's. */
	else if ((err = put(CAPS_LED_TRIGGER, "keyboard-matrix-capslock")))
		err = put(CAPS_LED_TRIGGER, "kbd-capslock");
	if (!err)
		caps_led_dark = dark;
}

/*
 * CPUs 1-9 go offline while the screen is dark: for the A53s, about 15 mA of the
 * 111 mA idle draw (2026-11-06-gemini-power-management, R1b). Only the CPUs this
 * program took down come back, so one the owner offlined stays off; at start, when
 * a previous run may have died with the screen dark, a lit screen brings back the
 * offline A53s. An A72 (CPU8-9) is taken only if it is online, which means the
 * mt6797-a72 module brought it up, and comes back only if this program took it:
 * bringing one up without that module never returns. They come back in order, so
 * CPU8 is first back to a cluster that went down, as the module requires. The
 * writes run in a child, since each CPU takes about 30 ms and a wake must not wait
 * for them; a new switch first waits for the previous one.
 */
#define FIRST_CPU 1
#define LAST_A53 7
#define LAST_CPU 9
/* 1 dark, 0 lit, -1 not yet switched. */
static int cpus_dark = -1;
static unsigned int cpus_taken;
static pid_t cpus_child = -1;

#ifndef CPU_SYSFS
#define CPU_SYSFS "/sys/devices/system/cpu"
#endif

static void cpu_online_path(char *path, size_t size, int cpu)
{
	snprintf(path, size, CPU_SYSFS "/cpu%d/online", cpu);
}

static void cpus(int dark)
{
	char path[64];
	unsigned int mask = 0;
	pid_t pid;
	int cpu, online;

	if (dark == cpus_dark)
		return;
	if (cpus_child > 0)
		waitpid(cpus_child, NULL, 0);
	cpus_child = -1;
	for (cpu = FIRST_CPU; cpu <= LAST_CPU; cpu++) {
		cpu_online_path(path, sizeof(path), cpu);
		online = read_number(path);
		if (dark ? online == 1 :
		    cpus_dark < 0 ? online == 0 && cpu <= LAST_A53 :
		    !!(cpus_taken & (1U << cpu)))
			mask |= 1U << cpu;
	}
	cpus_dark = dark;
	cpus_taken = dark ? mask : 0;
	if (!mask)
		return;
	pid = fork();
	if (pid < 0) {
		say("cannot switch the CPUs: %s\n", strerror(errno));
		return;
	}
	if (pid > 0) {
		cpus_child = pid;
		return;
	}
	for (cpu = FIRST_CPU; cpu <= LAST_CPU; cpu++) {
		if (!(mask & (1U << cpu)))
			continue;
		cpu_online_path(path, sizeof(path), cpu);
		if (put(path, dark ? "0" : "1"))
			say("cpu%d did not go %s\n", cpu, dark ? "offline" : "online");
	}
	_exit(0);
}

/* The lid's state from the switch itself, -1 if it can't be read. */
static int lid_now(int fd)
{
	unsigned long sw[(SW_MAX + 8 * sizeof(long)) / (8 * sizeof(long))] = { 0 };

	if (ioctl(fd, EVIOCGSW(sizeof(sw)), sw) < 0)
		return -1;
	return !!(sw[SW_LID / (8 * sizeof(long))] & (1UL << (SW_LID % (8 * sizeof(long)))));
}

/*
 * Suspend to memory while the lid stays closed, only when the kernel offers
 * "deep": without the SPM sleep module, "mem" would mean s2idle, which this
 * policy does not use. A refusal (a charger attached, a radio on) is reported
 * once and waits for the next close. After a timer wake with the lid still
 * closed it suspends again, unless that suspend came back at once.
 */
static void lid_suspend(int fd)
{
	char modes[64] = "";
	int mfd, n, ret;

	mfd = open(MEM_SLEEP, O_RDONLY | O_CLOEXEC);
	if (mfd < 0)
		return;
	n = read(mfd, modes, sizeof(modes) - 1);
	close(mfd);
	if (n <= 0 || !strstr(modes, "[deep]"))
		return;
	if (cpus_child > 0)
		waitpid(cpus_child, NULL, 0);
	cpus_child = -1;
	for (;;) {
		long long start = now_ms();

		ret = put(POWER_STATE, "mem");
		if (ret) {
			say("lid suspend refused: %s\n", strerror(-ret));
			return;
		}
		if (lid_now(fd) != 1)
			return;
		if (now_ms() - start < SUSPEND_MIN_MS) {
			say("lid suspend woke at once; staying up\n");
			return;
		}
	}
}

static volatile sig_atomic_t blank_set;

static void on_blank_set(int sig)
{
	(void)sig;
	blank_set = 1;
}

int main(void)
{
	char lid[512], keyboard[512], pmic_keys[512];
	unsigned long sw[(SW_MAX + 8 * sizeof(long)) / (8 * sizeof(long))] = { 0 };
	struct input_event ev;
	struct pollfd fds[3];
	int fd, kfd, pfd, closed, fn = 0, restore = -1, quick = 0, was_blanked = 0, wait = 0;
	int suspend_due = 0;
	long long last_input = now_ms();
	/* No SA_RESTART: the signal must end the poll. */
	struct sigaction blank_action = { .sa_handler = on_blank_set };

	sigaction(SIGUSR1, &blank_action, NULL);

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
	/* A previous run may have died at the end of a fade, with no blank to follow. */
	if (!closed && !console_blanked() && read_number(BL_POWER) != 0)
		put(BL_POWER, "0");
	kfd = open_events(keyboard);
	if (kfd < 0)
		say("no keyboard events; brightness keys off\n");
	pfd = find_input(PMIC_KEYS_NAME, pmic_keys, sizeof(pmic_keys)) ? open_events(pmic_keys) : -1;
	if (pfd < 0)
		say("no PMIC key events; Esc and the side key don't count as input\n");
	/* poll ignores a negative fd. */
	fds[0] = (struct pollfd){ .fd = fd, .events = POLLIN };
	fds[1] = (struct pollfd){ .fd = kfd, .events = POLLIN };
	fds[2] = (struct pollfd){ .fd = pfd, .events = POLLIN };
	/* After a key, look again soon: the kernel wakes the console just after it. */
	for (;;) {
		int blanked, i;

		if (poll(fds, 3, quick > 0 ? 50 : wait) < 0) {
			if (errno != EINTR)
				break;
			for (i = 0; i < 3; i++)
				fds[i].revents = 0;
		}
		if (blank_set) {
			blank_set = 0;
			last_input = now_ms();
			quick = 20;
		}
		blanked = console_blanked();
		/* No backlight reads -1, which must not count as dark. */
		caps_led(closed || blanked || read_number(BL_POWER) > 0);
		cpus(closed || blanked);
		if (suspend_due) {
			suspend_due = 0;
			if (closed)
				lid_suspend(fd);
		}

		if (quick > 0)
			quick--;
		wait = -1;
		if (!!blanked != was_blanked) {
			say("console %s\n", blanked ? "blanked" : "unblanked");
			was_blanked = !!blanked;
			/* Any wake restarts the kernel's deadline, whatever caused it. */
			if (!blanked)
				last_input = now_ms();
			/*
			 * The kernel is lighting it again at the dim level, a moment after it
			 * reports unblanked; then back up to the owner's. The key that woke it
			 * must not cancel this, so it waits, like any other input.
			 */
			if (!blanked && restore >= 0) {
				for (i = 0; i < 20 && read_number(BL_POWER) != 0; i++)
					poll(NULL, 0, 25);
				/* Only the panel's link does that; simplefb has none. A lid may have closed. */
				if (i == 20 && !console_blanked())
					put(BL_POWER, "0");
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
					/*
					 * The kernel's blank timer is a coarse one, up to 2 s late,
					 * so the light goes out here at the end of the fade. The
					 * blank follows by itself and wakes the light again.
					 */
					if (fade(level, DIM_LEVEL, FADE_DOWN_STEPS, FADE_DOWN_MS,
						 fds, 3)) {
						/* A closing lid must not relight; its event handles this. */
						if (!(fds[0].revents & POLLIN)) {
							undim(restore);
							restore = -1;
						}
					} else {
						put(BL_POWER, "4");
						caps_led(1);
					}
				}
			} else if (restore >= 0 && (seconds * 1000 <= FADE_DOWN_LEAD_MS || left > 0)) {
				/* The deadline moved or went, with no blank after all. */
				undim(restore);
				restore = -1;
			} else if (restore >= 0 && left < -(FADE_DOWN_LEAD_MS + BLANK_OVERDUE_MS)) {
				undim(restore);
				restore = -1;
				last_input = now_ms();
			}
			/* Wake exactly when the fade has to start; from then, the blank is due. */
			if (seconds > 0)
				wait = seconds * 1000 > FADE_DOWN_LEAD_MS && left > 0 ? (int)left : 1000;
		}
		for (i = 1; i < 3; i++) {
			if (!(fds[i].revents & POLLIN) ||
			    read(fds[i].fd, &ev, sizeof(ev)) != sizeof(ev) || ev.type != EV_KEY)
				continue;
			last_input = event_ms(&ev);
			quick = 20;
			if (restore >= 0 && !blanked && !(fds[0].revents & POLLIN)) {
				undim(restore);
				restore = -1;
			}
			if (i != 1)
				continue;
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
		suspend_due = closed;
		quick = 20;
		if (restore >= 0) {
			/* The lid module owns the light now. */
			set_brightness(restore);
			restore = -1;
		}
		last_input = event_ms(&ev);
	}
	say("lid event stream ended\n");
	sleep(60);
	return 1;
}
