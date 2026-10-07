/* SPDX-License-Identifier: MIT */
/* Scripted netlink kernel for the production join-connect transport. */
#define JOIN_CONNECT_FIXTURE 1
#include "../helper/join-connect.c"
#undef main
#include <assert.h>

/* Script: an ordered list of replies the fake kernel delivers, each tagged
 * with the request count after which it becomes available and its sender pid.
 */
struct scripted { unsigned after_sends; uint32_t from_pid; unsigned char data[REPLY_BYTES + 64]; size_t length; };
static struct scripted script[8];
static unsigned script_count, delivered, sends;
static unsigned char sent[4][512]; static size_t sent_length[4];
static uint64_t clock_ms;

static int transport_open(void) { return 7; }
static int transport_send(int fd, const void *data, size_t length)
{ assert(fd == 7 && sends < 4); memcpy(sent[sends], data, length); sent_length[sends] = length; sends++; return 0; }
static int transport_receive(int fd, struct reply *r)
{
	assert(fd == 7);
	for (unsigned i = delivered; i < script_count; i++) {
		if (script[i].after_sends > sends)
			break;
		delivered = i + 1;
		/* Like the real transport: a datagram longer than the buffer is refused. */
		if (script[i].length > sizeof(r->data))
			return -1;
		memcpy(r->data, script[i].data, script[i].length);
		r->length = script[i].length; r->from_pid = script[i].from_pid;
		return 0;
	}
	clock_ms += RECEIVE_TIMEOUT_MS;  /* a bounded receive timed out */
	return -1;
}
static void transport_close(int fd) { assert(fd == 7); }
static uint64_t now_ms(void) { return clock_ms; }

/* The kernel stamps the requester's own port ID into every reply header
 * (netlink_ack, genlmsg_put_reply); the fixture uses a non-zero value so a
 * header-PID check would be caught. Sender identity is the sockaddr PID.
 */
#define HEADER_PID 777U
static size_t ack_bytes(unsigned char *out, uint32_t seq, int error)
{
	struct nlmsghdr h = { .nlmsg_len = NLMSG_LENGTH(sizeof(struct nlmsgerr)), .nlmsg_type = NLMSG_ERROR,
			      .nlmsg_seq = seq, .nlmsg_pid = HEADER_PID };
	struct nlmsgerr e = { .error = error };
	memcpy(out, &h, sizeof(h)); memcpy(out + NLMSG_HDRLEN, &e, sizeof(e));
	return NLMSG_ALIGN(h.nlmsg_len);
}
/* A family reply like the real nl80211 one: name, then a large operations
 * list, then the family id, so the id sits beyond the first 512 bytes.
 */
static size_t family_bytes_sized(unsigned char *out, uint32_t seq, uint16_t id, uint16_t ops_bytes)
{
	struct genlmsghdr g = { .cmd = CTRL_CMD_NEWFAMILY, .version = 2 };
	static const char name[GENL_NAMSIZ] = "nl80211";
	struct nlattr n = { .nla_len = sizeof(n) + GENL_NAMSIZ, .nla_type = CTRL_ATTR_FAMILY_NAME };
	struct nlattr ops = { .nla_len = (uint16_t)(sizeof(ops) + ops_bytes), .nla_type = CTRL_ATTR_OPS | NLA_F_NESTED };
	struct nlattr a = { .nla_len = sizeof(a) + sizeof(id), .nla_type = CTRL_ATTR_FAMILY_ID };
	size_t off = NLMSG_HDRLEN;
	struct nlmsghdr h = { .nlmsg_type = GENL_ID_CTRL, .nlmsg_seq = seq, .nlmsg_pid = HEADER_PID };
	memcpy(out + off, &g, sizeof(g)); off += NLA_ALIGN4(sizeof(g));
	memcpy(out + off, &n, sizeof(n)); memcpy(out + off + sizeof(n), name, GENL_NAMSIZ); off += NLA_ALIGN4(n.nla_len);
	if (ops_bytes) { memcpy(out + off, &ops, sizeof(ops)); memset(out + off + sizeof(ops), 0x5a, ops_bytes); off += NLA_ALIGN4(ops.nla_len); }
	memcpy(out + off, &a, sizeof(a)); memcpy(out + off + sizeof(a), &id, sizeof(id)); off += NLA_ALIGN4(a.nla_len);
	h.nlmsg_len = (uint32_t)off; memcpy(out, &h, sizeof(h));
	return NLMSG_ALIGN(off);
}
static size_t family_bytes(unsigned char *out, uint32_t seq, uint16_t id)
{ return family_bytes_sized(out, seq, id, 0); }
static void add_large_family(unsigned after, uint32_t pid, uint32_t seq, uint16_t id, uint16_t ops_bytes)
{
	struct scripted *s = &script[script_count++];
	s->after_sends = after; s->from_pid = pid; s->length = family_bytes_sized(s->data, seq, id, ops_bytes);
}
static void add_ack(unsigned after, uint32_t pid, uint32_t seq, int error)
{
	struct scripted *s = &script[script_count++];
	s->after_sends = after; s->from_pid = pid; s->length = ack_bytes(s->data, seq, error);
}
static void add_family(unsigned after, uint32_t pid, uint32_t seq, uint16_t id)
{
	struct scripted *s = &script[script_count++];
	s->after_sends = after; s->from_pid = pid; s->length = family_bytes(s->data, seq, id);
}
/* The real kernel may deliver the lookup reply and its acknowledgement in one datagram. */
static void add_family_with_ack(unsigned after, uint32_t pid, uint32_t seq, uint16_t id)
{
	struct scripted *s = &script[script_count++];
	s->after_sends = after; s->from_pid = pid;
	s->length = family_bytes(s->data, seq, id);
	s->length += ack_bytes(s->data + s->length, seq, 0);
}
static void reset(void) { memset(script, 0, sizeof(script)); script_count = delivered = sends = 0; clock_ms = 1000; }
static int run(void)
{
	char *argv[] = {"join-connect", "wlan0", "net", "5200", "02:11:22:33:44:55", NULL};
	return join_connect_main(5, argv);
}
static uint32_t sent_seq(unsigned i) { struct nlmsghdr h; memcpy(&h, sent[i], sizeof(h)); return h.nlmsg_seq; }
static uint16_t sent_type(unsigned i) { struct nlmsghdr h; memcpy(&h, sent[i], sizeof(h)); return h.nlmsg_type; }

/* if_nametoindex needs no real interface in the fixture. */
unsigned int if_nametoindex(const char *name) { return strcmp(name, "wlan0") ? 0 : 3; }

int main(void)
{
	/* Happy path: family reply + its ack, then the connect ack with error 0. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c); add_ack(1, 0, FAMILY_SEQ, 0); add_ack(2, 0, CONNECT_SEQ, 0);
	assert(run() == 0 && sends == 2 && sent_seq(0) == FAMILY_SEQ && sent_seq(1) == CONNECT_SEQ && sent_type(1) == 0x1c);
	/* A real-sized nl80211 family reply (id after ~2 KiB of operations) is parsed. */
	reset(); add_large_family(1, 0, FAMILY_SEQ, 0x1c, 2000); add_ack(1, 0, FAMILY_SEQ, 0); add_ack(2, 0, CONNECT_SEQ, 0);
	assert(script[0].length > 512 && run() == 0 && sends == 2 && sent_type(1) == 0x1c);
	/* A reply longer than the receive buffer is refused as truncated; no connect is sent. */
	reset(); add_large_family(1, 0, FAMILY_SEQ, 0x1c, REPLY_BYTES); add_ack(1, 0, FAMILY_SEQ, 0);
	assert(script[0].length > REPLY_BYTES && run() == 2 && sends == 1);
	/* Lookup reply and acknowledgement in one datagram are both consumed. */
	reset(); add_family_with_ack(1, 0, FAMILY_SEQ, 0x1c); add_ack(2, 0, CONNECT_SEQ, 0);
	assert(run() == 0 && sends == 2 && sent_type(1) == 0x1c);
	/* Kernel -95 on the connect is retained and reported as exit 3. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c); add_ack(1, 0, FAMILY_SEQ, 0); add_ack(2, 0, CONNECT_SEQ, -EOPNOTSUPP);
	assert(run() == 3 && sends == 2);
	/* The family ack arriving late cannot acknowledge the connect: the connect
	 * is only sent after that ack was consumed, so a script that never answers
	 * the connect ends at the deadline with exit 2 and exactly one connect sent. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c); add_ack(1, 0, FAMILY_SEQ, 0);
	assert(run() == 2 && sends == 2 && sent_seq(1) == CONNECT_SEQ && clock_ms >= 1000 + TOTAL_DEADLINE_MS);
	/* A stale family-sequence ack delivered after the connect is ignored. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c); add_ack(1, 0, FAMILY_SEQ, 0); add_ack(2, 0, FAMILY_SEQ, 0);
	assert(run() == 2 && sends == 2);
	/* Non-kernel origin replies are ignored even with the right sequence. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c); add_ack(1, 0, FAMILY_SEQ, 0); add_ack(2, 4242, CONNECT_SEQ, 0);
	assert(run() == 2);
	/* Family lookup without an ack never sends the connect. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c);
	assert(run() == 2 && sends == 1);
	/* Family lookup acked with an error never sends the connect. */
	reset(); add_family(1, 0, FAMILY_SEQ, 0x1c); add_ack(1, 0, FAMILY_SEQ, -ENOENT);
	assert(run() == 2 && sends == 1);
	/* No reply at all: bounded by the deadline, one request, no retry. */
	reset(); assert(run() == 2 && sends == 1 && clock_ms >= 1000 + TOTAL_DEADLINE_MS);
	puts("transport=pass");
	return 0;
}
