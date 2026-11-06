// SPDX-License-Identifier: GPL-2.0-only
/*
 * rumble: play one FF_RUMBLE effect on the regulator-haptic input device.
 *
 * Usage: rumble /dev/input/eventN MILLISECONDS
 *
 * Refuses a device that is not named "regulator-haptic", has no FF_RUMBLE,
 * or a length outside 10-300 ms. Waits for the effect to end, then removes
 * it and closes the device, which also stops the motor.
 */
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define NAME "regulator-haptic"
#define MIN_MS 10
#define MAX_MS 300

static int fail(const char *what)
{
	fprintf(stderr, "rumble: %s: %s\n", what, strerror(errno));
	return 1;
}

int main(int argc, char **argv)
{
	unsigned long ff[(FF_CNT + 8 * sizeof(long) - 1) / (8 * sizeof(long))];
	struct ff_effect effect;
	struct input_event play;
	struct timespec wait;
	char name[64] = "";
	char *end;
	long ms;
	int fd;

	if (argc != 3) {
		fprintf(stderr, "usage: rumble /dev/input/eventN MILLISECONDS\n");
		return 2;
	}
	ms = strtol(argv[2], &end, 10);
	if (*argv[2] == '\0' || *end != '\0' || ms < MIN_MS || ms > MAX_MS) {
		fprintf(stderr, "rumble: length must be %d-%d ms\n", MIN_MS, MAX_MS);
		return 2;
	}

	fd = open(argv[1], O_RDWR);
	if (fd < 0)
		return fail(argv[1]);
	if (ioctl(fd, EVIOCGNAME(sizeof(name) - 1), name) < 0)
		return fail("EVIOCGNAME");
	if (strcmp(name, NAME) != 0) {
		fprintf(stderr, "rumble: %s is \"%s\", not \"%s\"\n", argv[1], name, NAME);
		return 1;
	}
	memset(ff, 0, sizeof(ff));
	if (ioctl(fd, EVIOCGBIT(EV_FF, sizeof(ff)), ff) < 0)
		return fail("EVIOCGBIT");
	if (!(ff[FF_RUMBLE / (8 * sizeof(long))] & (1UL << (FF_RUMBLE % (8 * sizeof(long)))))) {
		fprintf(stderr, "rumble: %s has no FF_RUMBLE\n", argv[1]);
		return 1;
	}

	memset(&effect, 0, sizeof(effect));
	effect.type = FF_RUMBLE;
	effect.id = -1;
	effect.u.rumble.strong_magnitude = 0xffff;
	effect.replay.length = ms;
	if (ioctl(fd, EVIOCSFF, &effect) < 0)
		return fail("EVIOCSFF");

	memset(&play, 0, sizeof(play));
	play.type = EV_FF;
	play.code = effect.id;
	play.value = 1;
	if (write(fd, &play, sizeof(play)) != sizeof(play))
		return fail("play");
	printf("rumble: %s effect %d for %ld ms\n", argv[1], effect.id, ms);

	ms += 50;
	wait.tv_sec = ms / 1000;
	wait.tv_nsec = (ms % 1000) * 1000000L;
	nanosleep(&wait, NULL);

	if (ioctl(fd, EVIOCRMFF, effect.id) < 0)
		return fail("EVIOCRMFF");
	close(fd);
	return 0;
}
