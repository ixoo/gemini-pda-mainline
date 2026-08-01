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

#define TRIGGER_PATH "/sys/kernel/gemini_da921x_uevent_untagged_dispatch"
#define STAGE_PATH "/sys/kernel/gemini_da921x_dual_modalias_stage"
#define READY_STATE \
	"attempts=0 entries=0 returns=0 baseline_sockets=-1 sockets=-1 listeners=-1 allocations=-1 broadcasts=-1 retval=-1\n"
#define PASSED_STATE \
	"attempts=1 entries=1 returns=1 baseline_sockets=1 sockets=1 listeners=1 allocations=1 broadcasts=1 retval=0\n"
#define EXPECTED_HEADER \
	"add@/devices/platform/1100e000.i2c/i2c-1/1-0068"
#define EXPECTED_LENGTH 293
#define RECEIVE_TIMEOUT_MS 1500
#define DUPLICATE_TIMEOUT_MS 250

static const char *const expected_entries[] = {
	"ACTION=add",
	"DEVPATH=/devices/platform/1100e000.i2c/i2c-1/1-0068",
	"SUBSYSTEM=i2c",
	"OF_NAME=regulator",
	"OF_FULLNAME=/i2c@1100e000/regulator@68",
	"OF_COMPATIBLE_0=dlg,da9214-legacy",
	"OF_COMPATIBLE_N=1",
	"MODALIAS=of:NregulatorT(null)Cdlg,da9214-legacy",
};

static void fail(const char *step)
{
	fprintf(stderr, "untagged_dispatch_result=FAIL\nfailure=%s errno=%d\n",
		step, errno);
	exit(EXIT_FAILURE);
}

static void require_text(const char *path, const char *expected,
			 const char *step)
{
	char buf[192];
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

static size_t validate_payload(const unsigned char *data, size_t length)
{
	const size_t header_length = sizeof(EXPECTED_HEADER);
	const unsigned char *cursor;
	const unsigned char *end = data + length;
	size_t i;
	size_t digits = 0;

	if (length != EXPECTED_LENGTH ||
	    memcmp(data, EXPECTED_HEADER, header_length)) {
		errno = EPROTO;
		fail("payload-header");
	}
	cursor = data + header_length;
	for (i = 0; i < sizeof(expected_entries) / sizeof(expected_entries[0]);
	     i++) {
		size_t entry_length = strlen(expected_entries[i]) + 1;

		if ((size_t)(end - cursor) < entry_length ||
		    memcmp(cursor, expected_entries[i], entry_length)) {
			errno = EPROTO;
			fail("payload-fixed-entry");
		}
		cursor += entry_length;
	}
	if ((size_t)(end - cursor) < sizeof("SEQNUM=0") ||
	    memcmp(cursor, "SEQNUM=", sizeof("SEQNUM=") - 1)) {
		errno = EPROTO;
		fail("payload-seqnum-prefix");
	}
	cursor += sizeof("SEQNUM=") - 1;
	while (cursor < end && *cursor >= '0' && *cursor <= '9') {
		digits++;
		cursor++;
	}
	if (!digits || cursor + 1 != end || *cursor) {
		errno = EPROTO;
		fail("payload-seqnum-shape");
	}
	return digits;
}

int main(void)
{
	struct sockaddr_nl bound = { 0 };
	struct sockaddr_nl source = { 0 };
	struct sockaddr_nl address = {
		.nl_family = AF_NETLINK,
		.nl_pid = getpid(),
		.nl_groups = 1,
	};
	unsigned char control[CMSG_SPACE(sizeof(struct ucred))] = { 0 };
	unsigned char payload[512];
	struct iovec iov = {
		.iov_base = payload,
		.iov_len = sizeof(payload),
	};
	struct msghdr message = {
		.msg_name = &source,
		.msg_namelen = sizeof(source),
		.msg_iov = &iov,
		.msg_iovlen = 1,
		.msg_control = control,
		.msg_controllen = sizeof(control),
	};
	struct pollfd pfd;
	struct cmsghdr *cmsg;
	struct ucred *credentials = NULL;
	socklen_t bound_len = sizeof(bound);
	const char trigger[] = "probe\n";
	int receive_buffer = 16384;
	int pass_credentials = 1;
	ssize_t received;
	ssize_t written;
	size_t seqnum_digits;
	int trigger_fd;
	int poll_ret;
	int fd;

	if (geteuid()) {
		errno = EPERM;
		fail("not-root");
	}
	require_text(STAGE_PATH, "21\n", "pre-stage");
	require_text(TRIGGER_PATH, READY_STATE, "pre-state");

	fd = socket(AF_NETLINK, SOCK_DGRAM | SOCK_CLOEXEC,
		    NETLINK_KOBJECT_UEVENT);
	if (fd < 0)
		fail("socket");
	if (setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &receive_buffer,
		       sizeof(receive_buffer)))
		fail("receive-buffer");
	if (setsockopt(fd, SOL_SOCKET, SO_PASSCRED, &pass_credentials,
		       sizeof(pass_credentials)))
		fail("pass-credentials");
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

	require_text(STAGE_PATH, "22\n", "post-stage");
	require_text(TRIGGER_PATH, PASSED_STATE, "post-state");
	pfd.fd = fd;
	pfd.events = POLLIN;
	pfd.revents = 0;
	poll_ret = poll(&pfd, 1, RECEIVE_TIMEOUT_MS);
	if (poll_ret < 0)
		fail("poll");
	if (poll_ret != 1 || !(pfd.revents & POLLIN)) {
		errno = ETIMEDOUT;
		fail("receipt-timeout");
	}
	received = recvmsg(fd, &message, MSG_DONTWAIT);
	if (received < 0)
		fail("recvmsg");
	if (message.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) {
		errno = EMSGSIZE;
		fail("receipt-truncated");
	}
	if (message.msg_namelen != sizeof(source) ||
	    source.nl_family != AF_NETLINK || source.nl_pid ||
	    source.nl_groups != 1) {
		errno = EPROTO;
		fail("source-identity");
	}
	for (cmsg = CMSG_FIRSTHDR(&message); cmsg;
	     cmsg = CMSG_NXTHDR(&message, cmsg)) {
		if (cmsg->cmsg_level == SOL_SOCKET &&
		    cmsg->cmsg_type == SCM_CREDENTIALS &&
		    cmsg->cmsg_len == CMSG_LEN(sizeof(struct ucred))) {
			if (credentials) {
				errno = EPROTO;
				fail("duplicate-credentials");
			}
			credentials = (struct ucred *)CMSG_DATA(cmsg);
		}
	}
	if (!credentials || credentials->pid || credentials->uid ||
	    credentials->gid) {
		errno = EPROTO;
		fail("credentials");
	}
	seqnum_digits = validate_payload(payload, (size_t)received);

	pfd.revents = 0;
	poll_ret = poll(&pfd, 1, DUPLICATE_TIMEOUT_MS);
	if (poll_ret < 0)
		fail("duplicate-poll");
	if (poll_ret || pfd.revents) {
		errno = EPROTO;
		fail("duplicate-delivery");
	}
	if (close(fd))
		fail("listener-close");

	printf("trigger_write=exact-probe-token\n");
	printf("listener_receipt=one-exact-datagram\n");
	printf("receipt_bytes=%zd\n", received);
	printf("receipt_entries=9\nseqnum_digits=%zu\n", seqnum_digits);
	printf("receipt_source=kernel-group-1\nreceipt_credentials=root\n");
	printf("duplicate_receipt=none-bounded-timeout\n");
	printf("untagged_dispatch_result=PASS\n");
	return EXIT_SUCCESS;
}
