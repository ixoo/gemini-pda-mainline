// SPDX-License-Identifier: MIT
/* join-connect: one NL80211_CMD_CONNECT request with the privacy flag set.
 *
 * cfg80211's station management entity looks the target BSS up with the
 * request's privacy setting and, on a miss, issues a directed scan. A keyless
 * `iw connect` leaves privacy clear, so a protected AP never matches and the
 * one-shot hardware scan refuses the fallback. This helper sends the same
 * connect request with NL80211_ATTR_PRIVACY set and open-system
 * authentication, so the entity finds the already scanned BSS and proceeds
 * to authenticate and associate without any scan. Phase C1 adds the WPA2-PSK
 * CCMP security parameters and the fixed RSN element the association
 * request needs; the element holds no secret. It still carries no key and
 * no data path; cfg80211 and mac80211 then drive the bounded exchange the
 * driver admits.
 *
 * Transport: two requests with distinct sequence numbers, each answered only
 * by a kernel-origin reply carrying its own sequence; the family lookup's
 * acknowledgement is consumed before the connect request is sent; every
 * receive is bounded and the whole exchange has one deadline; no retry.
 *
 * Usage: join-connect IFNAME SSID FREQ_MHZ BSSID
 *        join-connect --dump IFINDEX SSID FREQ_MHZ BSSID   (print the request, send nothing)
 *        join-connect --family-lookup NAME   (generic netlink lookup only; no connect)
 * Exit: 0 request acknowledged, 1 usage, 2 transport failure or deadline,
 *       3 kernel error (printed).
 *
 * Reply identity: the kernel is identified by the sender address
 * (sockaddr_nl.nl_pid == 0). The reply header's nlmsg_pid is the requester's
 * own port ID (netlink_ack() and genlmsg_put_reply() both stamp
 * NETLINK_CB(skb).portid / info->snd_portid), so it is not checked.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdalign.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <net/if.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <linux/genetlink.h>
#include <linux/netlink.h>
#include <linux/nl80211.h>

#define NLA_ALIGN4(len) (((len) + 3U) & ~3U)
#define SSID_MAX 32
#define FAMILY_SEQ 1U
#define CONNECT_SEQ 2U
#define RECEIVE_TIMEOUT_MS 500
#define TOTAL_DEADLINE_MS 2000
/* WPA2-PSK with CCMP for both ciphers, no management frame protection: the
 * target's advertised RSN parameters. Suite selectors are IEEE OUI 00-0F-AC.
 */
#define SUITE_CCMP 0x000fac04U
#define AKM_PSK 0x000fac02U
static const unsigned char RSN_ELEMENT[] = {
	0x30, 0x14,             /* RSN, 20 bytes */
	0x01, 0x00,             /* version 1 */
	0x00, 0x0f, 0xac, 0x04, /* group cipher CCMP */
	0x01, 0x00, 0x00, 0x0f, 0xac, 0x04, /* one pairwise cipher: CCMP */
	0x01, 0x00, 0x00, 0x0f, 0xac, 0x02, /* one AKM: PSK */
	0x00, 0x00,             /* RSN capabilities */
};

struct message {
	alignas(struct nlmsghdr) unsigned char data[512];
	unsigned int length;
};

/* A generic netlink reply is at most one page-sized message (the family
 * lookup for nl80211 carries its operation and group lists and exceeds 512
 * bytes); a datagram longer than this buffer is detected and refused.
 */
#define REPLY_BYTES 8192
struct reply {
	alignas(struct nlmsghdr) unsigned char data[REPLY_BYTES];
	size_t length, offset;
	uint32_t from_pid;
};

/* Transport seams; the fixture replaces these three with a scripted kernel. */
#ifndef JOIN_CONNECT_FIXTURE
static int transport_open(void)
{
	struct timeval tv = { .tv_sec = RECEIVE_TIMEOUT_MS / 1000,
			      .tv_usec = (RECEIVE_TIMEOUT_MS % 1000) * 1000 };
	int fd = socket(AF_NETLINK, SOCK_RAW | SOCK_CLOEXEC, NETLINK_GENERIC);

	if (fd < 0)
		return -1;
	if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv))) {
		close(fd);
		return -1;
	}
	return fd;
}

static int transport_send(int fd, const void *data, size_t length)
{
	struct sockaddr_nl kernel = { .nl_family = AF_NETLINK };

	return sendto(fd, data, length, 0, (struct sockaddr *)&kernel, sizeof(kernel)) ==
	       (ssize_t)length ? 0 : -1;
}

static int transport_receive(int fd, struct reply *r)
{
	struct sockaddr_nl from;
	socklen_t from_len = sizeof(from);
	/* MSG_TRUNC returns the datagram's real length, so truncation is visible. */
	ssize_t got = recvfrom(fd, r->data, sizeof(r->data), MSG_TRUNC, (struct sockaddr *)&from,
			       &from_len);

	if (got < 0 || (size_t)got > sizeof(r->data) || from_len < sizeof(from) ||
	    from.nl_family != AF_NETLINK)
		return -1;
	r->length = (size_t)got;
	r->from_pid = from.nl_pid;
	return 0;
}

static void transport_close(int fd)
{
	close(fd);
}

static uint64_t now_ms(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000U + (uint64_t)ts.tv_nsec / 1000000U;
}
#else
static int transport_open(void);
static int transport_send(int fd, const void *data, size_t length);
static int transport_receive(int fd, struct reply *r);
static void transport_close(int fd);
static uint64_t now_ms(void);
#endif

static int put(struct message *m, uint16_t type, const void *payload, uint16_t bytes)
{
	struct nlattr attr;
	unsigned int total = NLA_ALIGN4(sizeof(attr) + bytes);

	if (m->length + total > sizeof(m->data))
		return -1;
	attr.nla_type = type;
	attr.nla_len = (uint16_t)(sizeof(attr) + bytes);
	memset(m->data + m->length, 0, total);
	memcpy(m->data + m->length, &attr, sizeof(attr));
	if (bytes)
		memcpy(m->data + m->length + sizeof(attr), payload, bytes);
	m->length += total;
	((struct nlmsghdr *)m->data)->nlmsg_len = m->length;
	return 0;
}

static int put_u32(struct message *m, uint16_t type, uint32_t value)
{
	return put(m, type, &value, sizeof(value));
}

static void start(struct message *m, uint16_t family, uint32_t seq, uint8_t command,
		  uint8_t version)
{
	struct nlmsghdr *h = (struct nlmsghdr *)m->data;
	struct genlmsghdr g = { .cmd = command, .version = version };

	memset(m, 0, sizeof(*m));
	h->nlmsg_type = family;
	h->nlmsg_flags = NLM_F_REQUEST | NLM_F_ACK;
	h->nlmsg_seq = seq;
	h->nlmsg_pid = 0;
	memcpy(m->data + sizeof(*h), &g, sizeof(g));
	m->length = sizeof(*h) + NLA_ALIGN4(sizeof(g));
	h->nlmsg_len = m->length;
}

static int parse_bssid(const char *text, unsigned char out[6])
{
	unsigned int values[6];
	char tail;

	if (strlen(text) != 17 ||
	    sscanf(text, "%2x:%2x:%2x:%2x:%2x:%2x%c", &values[0], &values[1], &values[2],
		   &values[3], &values[4], &values[5], &tail) != 6)
		return -1;
	for (int i = 0; i < 6; i++) {
		if (text[i * 3] == '+' || text[i * 3] == '-' || text[i * 3 + 1] == '+' ||
		    text[i * 3 + 1] == '-')
			return -1;
		out[i] = (unsigned char)values[i];
	}
	/* Unicast, non-zero target only. */
	if ((out[0] & 1) || !(out[0] | out[1] | out[2] | out[3] | out[4] | out[5]))
		return -1;
	return 0;
}

static int parse_u32(const char *text, uint32_t minimum, uint32_t maximum, uint32_t *out)
{
	char *end;
	unsigned long value;

	errno = 0;
	if (!*text)
		return -1;
	value = strtoul(text, &end, 10);
	if (errno || *end || value < minimum || value > maximum)
		return -1;
	*out = (uint32_t)value;
	return 0;
}

static int build(struct message *m, uint16_t family, uint32_t ifindex, const char *ssid,
		 uint32_t freq, const unsigned char bssid[6])
{
	size_t ssid_len = strlen(ssid);

	if (!ssid_len || ssid_len > SSID_MAX)
		return -1;
	start(m, family, CONNECT_SEQ, NL80211_CMD_CONNECT, 0);
	if (put_u32(m, NL80211_ATTR_IFINDEX, ifindex) ||
	    put(m, NL80211_ATTR_SSID, ssid, (uint16_t)ssid_len) ||
	    put_u32(m, NL80211_ATTR_WIPHY_FREQ, freq) ||
	    put(m, NL80211_ATTR_MAC, bssid, 6) ||
	    put(m, NL80211_ATTR_PRIVACY, NULL, 0) ||
	    put_u32(m, NL80211_ATTR_AUTH_TYPE, NL80211_AUTHTYPE_OPEN_SYSTEM) ||
	    put_u32(m, NL80211_ATTR_WPA_VERSIONS, NL80211_WPA_VERSION_2) ||
	    put_u32(m, NL80211_ATTR_CIPHER_SUITES_PAIRWISE, SUITE_CCMP) ||
	    put_u32(m, NL80211_ATTR_CIPHER_SUITE_GROUP, SUITE_CCMP) ||
	    put_u32(m, NL80211_ATTR_AKM_SUITES, AKM_PSK) ||
	    put(m, NL80211_ATTR_IE, RSN_ELEMENT, sizeof(RSN_ELEMENT)))
		return -1;
	return 0;
}

/* Receive kernel-origin messages until one with the wanted sequence and type
 * class arrives, or the deadline passes. Messages from other sequences or
 * non-kernel senders are ignored; several messages in one datagram are walked
 * in order, and the remainder of a datagram after a match is kept for the
 * next call. Returns 0 and copies the message, else -1.
 */
enum want { WANT_ACK, WANT_DATA };

static int await(int fd, uint32_t seq, enum want want, uint64_t deadline, uint16_t family,
		 struct reply *scratch, struct nlmsghdr *out, size_t out_size)
{
	for (;;) {
		while (scratch->offset + sizeof(struct nlmsghdr) <= scratch->length) {
			struct nlmsghdr h;
			size_t remaining = scratch->length - scratch->offset;

			memcpy(&h, scratch->data + scratch->offset, sizeof(h));
			if (h.nlmsg_len < sizeof(h) || h.nlmsg_len > remaining) {
				scratch->length = scratch->offset = 0;
				break;
			}
			scratch->offset += NLMSG_ALIGN(h.nlmsg_len);
			if (h.nlmsg_seq != seq)
				continue;
			if (want == WANT_ACK && h.nlmsg_type != NLMSG_ERROR)
				continue;
			if (want == WANT_DATA && h.nlmsg_type != family)
				continue;
			if (h.nlmsg_len > out_size)
				return -1;
			memcpy(out, scratch->data + scratch->offset - NLMSG_ALIGN(h.nlmsg_len),
			       h.nlmsg_len);
			return 0;
		}
		if (now_ms() >= deadline)
			return -1;
		scratch->length = scratch->offset = 0;
		if (transport_receive(fd, scratch))
			continue;
		/* Only the kernel (sender port 0) may answer. */
		if (scratch->from_pid != 0)
			scratch->length = 0;
	}
}

static int ack_error(const struct nlmsghdr *h, int *kernel_error)
{
	struct nlmsgerr e;

	if (h->nlmsg_type != NLMSG_ERROR || h->nlmsg_len < NLMSG_LENGTH(sizeof(e)))
		return -1;
	memcpy(&e, NLMSG_DATA(h), sizeof(e));
	*kernel_error = -e.error;
	return 0;
}

static int family_id(int fd, uint64_t deadline, struct reply *scratch, struct reply *got,
		     const char *name, uint16_t *family)
{
	struct message m;
	int err = 0;
	size_t name_len = strlen(name) + 1;

	if (name_len < 2 || name_len > GENL_NAMSIZ)
		return -1;
	start(&m, GENL_ID_CTRL, FAMILY_SEQ, CTRL_CMD_GETFAMILY, 1);
	if (put(&m, CTRL_ATTR_FAMILY_NAME, name, (uint16_t)name_len) ||
	    transport_send(fd, m.data, m.length))
		return -1;
	if (await(fd, FAMILY_SEQ, WANT_DATA, deadline, GENL_ID_CTRL, scratch,
		  (struct nlmsghdr *)got->data, sizeof(got->data)))
		return -1;
	got->length = ((struct nlmsghdr *)got->data)->nlmsg_len;
	/* The lookup's own acknowledgement must be consumed before the connect
	 * request is sent, so no stale acknowledgement can be mistaken later.
	 */
	if (await(fd, FAMILY_SEQ, WANT_ACK, deadline, 0, scratch,
		  (struct nlmsghdr *)m.data, sizeof(m.data)) ||
	    ack_error((struct nlmsghdr *)m.data, &err) || err)
		return -1;
	{
		unsigned int offset = sizeof(struct nlmsghdr) + NLA_ALIGN4(sizeof(struct genlmsghdr));

		while (offset + sizeof(struct nlattr) <= got->length) {
			struct nlattr a;

			memcpy(&a, got->data + offset, sizeof(a));
			if (a.nla_len < sizeof(a) || offset + a.nla_len > got->length)
				return -1;
			if ((a.nla_type & NLA_TYPE_MASK) == CTRL_ATTR_FAMILY_ID &&
			    a.nla_len == sizeof(a) + sizeof(uint16_t)) {
				memcpy(family, got->data + offset + sizeof(a), sizeof(*family));
				return *family >= GENL_MIN_ID ? 0 : -1;
			}
			offset += NLA_ALIGN4(a.nla_len);
		}
	}
	return -1;
}

#ifdef JOIN_CONNECT_FIXTURE
#define main join_connect_main
#endif
int main(int argc, char **argv)
{
	struct message m;
	static struct reply scratch, lookup;
	unsigned char bssid[6];
	uint32_t freq, ifindex;
	int dump = argc == 6 && !strcmp(argv[1], "--dump");
	const char **args = (const char **)argv + (dump ? 2 : 1);

	if (argc == 3 && !strcmp(argv[1], "--family-lookup")) {
		/* Transport smoke test: one lookup with its data reply and its
		 * acknowledgement, no connect request, no interface.
		 */
		uint64_t deadline = now_ms() + TOTAL_DEADLINE_MS;
		int fd = transport_open();
		uint16_t family = 0;

		if (fd < 0 || family_id(fd, deadline, &scratch, &lookup, argv[2], &family)) {
			fputs("join-connect: family lookup failed\n", stderr);
			if (fd >= 0)
				transport_close(fd);
			return 2;
		}
		transport_close(fd);
		printf("family=%u\n", family);
		return 0;
	}
	if (argc != 5 && !dump) {
		fputs("usage: join-connect IFNAME SSID FREQ_MHZ BSSID | --dump IFINDEX SSID FREQ_MHZ BSSID | --family-lookup NAME\n",
		      stderr);
		return 1;
	}
	if (dump) {
		if (parse_u32(args[0], 1, 65535, &ifindex))
			return 1;
	} else {
		ifindex = if_nametoindex(args[0]);
		if (!ifindex || strcmp(args[0], "wlan0")) {
			fputs("join-connect: interface must be the one admitted wlan0\n", stderr);
			return 1;
		}
	}
	/* Only the admitted 5 GHz channel 40 is accepted by this helper. */
	if (parse_u32(args[2], 5200, 5200, &freq) || parse_bssid(args[3], bssid) ||
	    build(&m, dump ? 0x1234 : 0, ifindex, args[1], freq, bssid)) {
		fputs("join-connect: invalid SSID, frequency or BSSID\n", stderr);
		return 1;
	}
	if (dump) {
		for (unsigned int i = 0; i < m.length; i++)
			printf("%02x", m.data[i]);
		putchar('\n');
		return 0;
	}
	{
		uint64_t deadline = now_ms() + TOTAL_DEADLINE_MS;
		int fd = transport_open();
		uint16_t family = 0;
		int kernel_error = 0;
		struct message ack;

		if (fd < 0 || family_id(fd, deadline, &scratch, &lookup, "nl80211", &family)) {
			fputs("join-connect: nl80211 family lookup failed\n", stderr);
			if (fd >= 0)
				transport_close(fd);
			return 2;
		}
		((struct nlmsghdr *)m.data)->nlmsg_type = family;
		if (transport_send(fd, m.data, m.length) ||
		    await(fd, CONNECT_SEQ, WANT_ACK, deadline, 0, &scratch,
			  (struct nlmsghdr *)ack.data, sizeof(ack.data)) ||
		    ack_error((struct nlmsghdr *)ack.data, &kernel_error)) {
			fputs("join-connect: connect request not acknowledged within the deadline\n",
			      stderr);
			transport_close(fd);
			return 2;
		}
		transport_close(fd);
		printf("connect_request=%s errno=%d\n", kernel_error ? "refused" : "acknowledged",
		       kernel_error);
		return kernel_error ? 3 : 0;
	}
}
