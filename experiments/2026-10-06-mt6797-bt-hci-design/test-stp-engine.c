/* SPDX-License-Identifier: GPL-2.0-only */
/* Persistent STP engine and H:4 reassembly against the actual headers. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mt6797-stp-engine.h"
#include "btmt6797-h4.h"

struct sink {
	unsigned int packets, length, refuse;
	unsigned char last[STP_FULL_MAX_PAYLOAD];
};

static int deliver(void *context, const unsigned char *payload, unsigned int length)
{
	struct sink *s = context;

	if (s->refuse)
		return -1;
	s->packets++;
	s->length = length;
	memcpy(s->last, payload, length);
	return 0;
}

static unsigned char peer_seq;

/* Feed one peer data frame carrying ack, byte by byte. */
static int peer_send(struct stp_engine *e, unsigned int task, const unsigned char *p,
		     unsigned int n, unsigned int ack, unsigned long now)
{
	unsigned char wire[STP_FULL_MAX_FRAME];
	int bytes = stp_full_encode(wire, sizeof(wire), p, n, task, peer_seq, ack);
	int i, ret = 0;

	assert(bytes > 0);
	peer_seq = (peer_seq + 1) & 7;
	for (i = 0; i < bytes && !ret; i++)
		ret = stp_engine_rx(e, wire[i], now);
	return ret;
}

static int peer_ack(struct stp_engine *e, unsigned int ack, unsigned long now)
{
	unsigned char wire[4];
	int i, ret = 0;

	assert(stp_full_ack(wire, 4, ack) == 4);
	for (i = 0; i < 4 && !ret; i++)
		ret = stp_engine_rx(e, wire[i], now);
	return ret;
}

/* Drain the TX side in odd-sized chunks; return frames decoded by the peer. */
static unsigned int drain(struct stp_engine *e, struct stp_full_frame *frames,
			  unsigned char store[][STP_FULL_MAX_FRAME], unsigned int max,
			  unsigned long now)
{
	unsigned int n = 0, pending, chunk;
	unsigned char buf[STP_FULL_MAX_FRAME];
	unsigned int used = 0;

	while ((pending = stp_engine_tx_pending(e))) {
		chunk = pending > 5 ? 5 : pending;
		memcpy(buf + used, stp_engine_tx_bytes(e), chunk);
		used += chunk;
		assert(stp_engine_tx_done(e, chunk, now) == 0);
		if (e->frame_length == 0) {
			assert(n < max);
			memcpy(store[n], buf, used);
			assert(stp_full_decode(store[n], used, &frames[n]) >= 0);
			n++;
			used = 0;
		}
	}
	return n;
}

int main(void)
{
	static struct stp_engine e;
	static unsigned char store[16][STP_FULL_MAX_FRAME];
	struct stp_full_frame f[16];
	struct sink wmt = { 0 }, bt = { 0 };
	static const unsigned char ev1[] = { 0x04, 0x0e, 0x04, 0x01, 0x03, 0x0c, 0x00 };
	static const unsigned char wmt_ev[] = { 0x02, 0x06, 0x01, 0x00, 0x00 };
	static const unsigned char cmd[] = { 0x01, 0x03, 0x0c, 0x00 };
	unsigned int i, n;

	/* Adopt a negotiated link at tx 1, rx 1, ACK 0/0. */
	stp_engine_init(&e, 0);
	e.link.tx_next = 1;
	e.link.rx_next = 1;
	e.link.peer_ack = 0;
	e.link.local_ack = 0;
	e.link.host_ack = 0;
	peer_seq = 1;
	assert(stp_engine_bind(&e, STP_FULL_TASK_WMT, deliver, &wmt) == 0);
	assert(stp_engine_bind(&e, STP_FULL_TASK_BT, deliver, &bt) == 0);
	assert(stp_engine_bind(&e, STP_FULL_TASK_BT, deliver, &bt) == STP_ENGINE_EINVAL);

	/* Interleaved unsolicited frames reach the right client; one ACK covers both. */
	assert(peer_send(&e, STP_FULL_TASK_BT, ev1, sizeof(ev1), 0, 1) == 0);
	assert(peer_send(&e, STP_FULL_TASK_WMT, wmt_ev, sizeof(wmt_ev), 0, 1) == 0);
	assert(peer_send(&e, STP_FULL_TASK_BT, ev1, sizeof(ev1), 0, 1) == 0);
	assert(bt.packets == 2 && wmt.packets == 1 && bt.length == sizeof(ev1));
	assert(e.link.ack_owed && e.link.local_ack == 3);
	n = drain(&e, f, store, 16, 2);
	assert(n == 1 && f[0].task == STP_FULL_TASK_NONE && f[0].acknowledgement == 3);
	assert(!e.link.ack_owed && e.tx_acks == 1);

	/* Shared window: eight queued commands, only seven leave before an ACK. */
	for (i = 0; i < STP_ENGINE_QUEUE; i++)
		assert(stp_engine_queue_msg(&e, i & 1 ? STP_FULL_TASK_WMT : STP_FULL_TASK_BT,
					    cmd, sizeof(cmd)) == 0);
	assert(stp_engine_queue_msg(&e, STP_FULL_TASK_BT, cmd, sizeof(cmd)) ==
	       STP_ENGINE_ENOSPC);
	n = drain(&e, f, store, 16, 3);
	assert(n == 7 && e.link.tx_pending == 7 && e.count == 1);
	for (i = 0; i < n; i++)
		assert(f[i].sequence == ((1 + i) & 7) && f[i].length == sizeof(cmd));
	/* A piggyback ACK in an unsolicited event retires three frames. */
	assert(peer_send(&e, STP_FULL_TASK_BT, ev1, sizeof(ev1), 3, 10) == 0);
	assert(e.link.tx_pending == 4 && e.ack_progress == 10);
	n = drain(&e, f, store, 16, 11);
	assert(n == 1 && f[0].length == sizeof(cmd) && f[0].acknowledgement == 4);
	assert(!e.link.ack_owed && e.count == 0 && e.link.tx_pending == 5);
	assert(peer_ack(&e, 0, 12) == 0 && e.link.tx_pending == 0);

	/* Unbound task: refused, not delivered, no credit, link continues. */
	assert(stp_engine_unbind(&e, STP_FULL_TASK_BT) == 0);
	assert(stp_engine_unbind(&e, STP_FULL_TASK_BT) == STP_ENGINE_EINVAL);
	i = e.link.rx_next;
	assert(peer_send(&e, STP_FULL_TASK_BT, ev1, sizeof(ev1), 0, 13) == 0);
	assert(e.rx_refused == 1 && e.link.rx_next == i && bt.packets == 3);
	/* The peer resends the same sequence once the client is back. */
	peer_seq = (peer_seq - 1) & 7;
	assert(stp_engine_bind(&e, STP_FULL_TASK_BT, deliver, &bt) == 0);
	bt.refuse = 1;
	assert(peer_send(&e, STP_FULL_TASK_BT, ev1, sizeof(ev1), 0, 14) == 0);
	assert(e.rx_refused == 2 && e.link.rx_next == i);
	bt.refuse = 0;
	peer_seq = (peer_seq - 1) & 7;
	assert(peer_send(&e, STP_FULL_TASK_BT, ev1, sizeof(ev1), 0, 15) == 0);
	assert(bt.packets == 4 && e.link.rx_next == ((i + 1) & 7));
	assert(drain(&e, f, store, 16, 16) == 1);

	/* ACK timeout is terminal and drops the queue; later calls report it. */
	assert(stp_engine_queue_msg(&e, STP_FULL_TASK_WMT, cmd, sizeof(cmd)) == 0);
	assert(drain(&e, f, store, 16, 20) == 1 && e.link.tx_pending == 1);
	assert(stp_engine_queue_msg(&e, STP_FULL_TASK_WMT, cmd, sizeof(cmd)) == 0);
	assert(stp_engine_tick(&e, 119, 100) == 0);
	assert(stp_engine_tick(&e, 120, 100) == STP_ENGINE_ETIMEDOUT);
	assert(e.count == 0 && stp_engine_tx_pending(&e) == 0);
	assert(stp_engine_queue_msg(&e, STP_FULL_TASK_WMT, cmd, 4) == STP_ENGINE_EIO);
	assert(stp_engine_rx(&e, 0x80, 121) == STP_ENGINE_ETIMEDOUT);

	/* Malformed input is terminal. */
	stp_engine_init(&e, 0);
	for (i = 0; i < 3; i++)
		assert(stp_engine_rx(&e, 0x00, 1) == 0);
	assert(stp_engine_rx(&e, 0x00, 1) == STP_ENGINE_EPROTO);
	assert(stp_engine_fail(&e, 0) == 0 && e.failed == STP_ENGINE_EPROTO);
	puts("stp engine: routing, window, retirement, unbind, bounds, failures pass");
	return 0;
}
