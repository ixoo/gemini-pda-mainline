// SPDX-License-Identifier: GPL-2.0-or-later

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/kd.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int fail(const char *operation)
{
	fprintf(stderr, "console-unicode-mode: %s: %s\n", operation,
		strerror(errno));
	return 1;
}

int main(void)
{
	static const char utf8_output_mode[] = "\033%G";
	int mode = -1;
	int fd;

	fd = open("/dev/tty1", O_RDWR | O_CLOEXEC | O_NOCTTY);
	if (fd < 0)
		return fail("open /dev/tty1");
	if (ioctl(fd, KDSKBMODE, K_UNICODE) < 0) {
		close(fd);
		return fail("KDSKBMODE K_UNICODE");
	}
	if (ioctl(fd, KDGKBMODE, &mode) < 0) {
		close(fd);
		return fail("KDGKBMODE");
	}
	if (mode != K_UNICODE) {
		fprintf(stderr,
			"console-unicode-mode: readback=%d expected=%d\n",
			mode, K_UNICODE);
		close(fd);
		return 1;
	}
	if (write(fd, utf8_output_mode, sizeof(utf8_output_mode) - 1) !=
			(ssize_t)(sizeof(utf8_output_mode) - 1)) {
		close(fd);
		return fail("select UTF-8 output mode");
	}
	if (close(fd) < 0)
		return fail("close /dev/tty1");

	puts("console_keyboard_mode=K_UNICODE");
	puts("console_output_mode=UTF-8");
	return 0;
}
