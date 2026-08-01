// SPDX-License-Identifier: GPL-2.0-only

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <linux/netlink.h>
#include <poll.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#define TRIGGER_PATH "/sys/kernel/gemini_da921x_uevent_bounded_listener"
#define STAGE_PATH "/sys/kernel/gemini_da921x_dual_modalias_stage"
#define READY_STATE \
	"attempts=0 baseline_sockets=-1 sockets=-1 listeners=-1 broadcasts=-1\n"
#define PASSED_STATE \
	"attempts=1 baseline_sockets=1 sockets=1 listeners=1 broadcasts=0\n"
#define RECEIVE_TIMEOUT_MS 1500

static void fail(const char *step)
{
	fprintf(stderr, "bounded_listener_result=FAIL\nfailure=%s errno=%d\n",
		step, errno);
	exit(EXIT_FAILURE);
}

static void require_text(const char *path, const char *expected,
			 const char *step)
{
	char buf[160];
	ssize_t len;
	int fd;

	fd = open(path, O_RDONLY | O_CLOEXEC);
	if (fd < 0)
		fail(step);
	len = read(fd, buf, sizeof(buf) - 1);
	if (len < 0) {
		close(fd);
		fail(step);
	}
	if (close(fd))
		fail(step);
	buf[len] = '\0';
	if (strcmp(buf, expected)) {
		errno = EPROTO;
		fail(step);
	}
}

int main(void)
{
	struct sockaddr_nl bound = { 0 };
	struct sockaddr_nl address = {
		.nl_family = AF_NETLINK,
		.nl_pid = getpid(),
		.nl_groups = 1,
	};
	struct pollfd pfd;
	socklen_t bound_len = sizeof(bound);
	const char trigger[] = "probe\n";
	int receive_buffer = 16384;
	ssize_t written;
	int trigger_fd;
	int poll_ret;
	int fd;

	if (geteuid()) {
		errno = EPERM;
		fail("not-root");
	}
	require_text(STAGE_PATH, "20\n", "pre-stage");
	require_text(TRIGGER_PATH, READY_STATE, "pre-state");

	fd = socket(AF_NETLINK, SOCK_DGRAM | SOCK_CLOEXEC,
		    NETLINK_KOBJECT_UEVENT);
	if (fd < 0)
		fail("socket");
	if (setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &receive_buffer,
		       sizeof(receive_buffer)))
		fail("receive-buffer");
	if (bind(fd, (struct sockaddr *)&address, sizeof(address)))
		fail("bind");
	if (getsockname(fd, (struct sockaddr *)&bound, &bound_len))
		fail("getsockname");
	if (bound_len != sizeof(bound) || bound.nl_family != AF_NETLINK ||
	    bound.nl_pid != (unsigned int)getpid() || bound.nl_groups != 1) {
		errno = EPROTO;
		fail("bound-identity");
	}

	printf("listener_ready=1\nlistener_groups=0x%x\n", bound.nl_groups);
	fflush(stdout);
	trigger_fd = open(TRIGGER_PATH, O_WRONLY | O_CLOEXEC);
	if (trigger_fd < 0)
		fail("trigger-open");
	written = write(trigger_fd, trigger, sizeof(trigger) - 1);
	if (written != (ssize_t)(sizeof(trigger) - 1)) {
		if (written >= 0)
			errno = EIO;
		close(trigger_fd);
		fail("trigger-write");
	}
	if (close(trigger_fd))
		fail("trigger-close");

	require_text(STAGE_PATH, "21\n", "post-stage");
	require_text(TRIGGER_PATH, PASSED_STATE, "post-state");
	pfd.fd = fd;
	pfd.events = POLLIN;
	pfd.revents = 0;
	poll_ret = poll(&pfd, 1, RECEIVE_TIMEOUT_MS);
	if (poll_ret < 0)
		fail("poll");
	if (poll_ret || pfd.revents) {
		errno = EPROTO;
		fail("unexpected-delivery");
	}
	if (close(fd))
		fail("listener-close");

	printf("trigger_write=exact-probe-token\n");
	printf("listener_receipt=none-bounded-timeout\n");
	printf("bounded_listener_result=PASS\n");
	return EXIT_SUCCESS;
}
