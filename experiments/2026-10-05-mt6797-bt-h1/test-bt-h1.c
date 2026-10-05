/* SPDX-License-Identifier: GPL-2.0-only */
/* Task-0 reply routing over the shared link, using the actual headers. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp-state.h"
#include "wmt-full-stp-stream.h"

static int feed(unsigned int task, const unsigned char *wire, unsigned int bytes)
{
	struct wmt_full_stream stream;
	struct wmt_full_frame frame;
	unsigned int i;
	int kind = 0;

	wmt_full_stream_init(&stream);
	for (i = 0; i < bytes; i++) {
		kind = stp_task_stream_byte(&stream, task, wire[i], &frame);
		if (kind)
			return kind < 0 || i + 1 == bytes ? kind : -2;
	}
	return kind;
}

int main(void)
{
	static const unsigned char version_prefix[] = { 4, 14, 12, 1, 1, 16, 0 };
	static const unsigned char version_reply[] = {
		4, 14, 12, 1, 1, 16, 0, 7, 0x11, 0x22, 7, 70, 0, 0x33, 0x44,
	};
	static const unsigned char func_event[] = { 2, 6, 1, 0, 0 };
	unsigned char wire[64], ack[4], bad[sizeof(version_reply)];
	struct wmt_full_state state, before;
	int bytes, wmt_bytes, ack_bytes;

	/* Stream: the expected task only; ACK frames for either task. */
	bytes = stp_full_encode(wire, sizeof(wire), version_reply,
				sizeof(version_reply), STP_FULL_TASK_BT, 1, 0);
	assert(bytes == (int)sizeof(version_reply) + 6);
	assert(feed(STP_FULL_TASK_BT, wire, bytes) == 2);
	assert(feed(STP_FULL_TASK_WMT, wire, bytes) == -1);
	assert(feed(5, wire, bytes) == -1);
	ack_bytes = stp_full_ack(ack, sizeof(ack), 3);
	assert(feed(STP_FULL_TASK_BT, ack, ack_bytes) == 1);
	assert(feed(STP_FULL_TASK_WMT, ack, ack_bytes) == 1);
	wmt_bytes = stp_full_encode(wire + 32, 32, func_event, sizeof(func_event),
				    STP_FULL_TASK_WMT, 1, 0);
	assert(feed(STP_FULL_TASK_BT, wire + 32, wmt_bytes) == -1);
	assert(feed(STP_FULL_TASK_WMT, wire + 32, wmt_bytes) == 2);

	/* A WMT exchange, then a task-0 exchange on the same link. */
	wmt_full_state_init(&state);
	assert(wmt_full_sent(&state, 0) == 0);
	wmt_bytes = stp_full_encode(wire, sizeof(wire), func_event,
				    sizeof(func_event), STP_FULL_TASK_WMT, 0, 0);
	assert(wmt_full_receive(&state, wire, wmt_bytes, func_event,
				sizeof(func_event)) == 1);
	ack_bytes = stp_full_ack(ack, sizeof(ack), state.transport.local_ack);
	assert(ack_bytes == 4 && wmt_full_ack_sent(&state, 0) == 0);
	assert(wmt_full_finish(&state) == 0);
	assert(state.transport.tx_next == 1 && state.transport.rx_next == 1);

	assert(wmt_full_sent(&state, 1) == 0);
	bytes = stp_full_encode(wire, sizeof(wire), version_reply,
				sizeof(version_reply), STP_FULL_TASK_BT, 1, 1);
	/* Wrong task binding, prefix mismatch and wrong length all refuse
	 * without changing the link or the event state.
	 */
	before = state;
	assert(wmt_full_receive_task(&state, wire, bytes, STP_FULL_TASK_WMT,
				     version_prefix, sizeof(version_prefix),
				     sizeof(version_reply)) == -1);
	assert(!memcmp(&state, &before, sizeof(state)));
	memcpy(bad, version_prefix, sizeof(version_prefix));
	bad[6] = 1;
	assert(wmt_full_receive_task(&state, wire, bytes, STP_FULL_TASK_BT, bad,
				     sizeof(version_prefix),
				     sizeof(version_reply)) == -1);
	assert(wmt_full_receive_task(&state, wire, bytes, STP_FULL_TASK_BT,
				     version_prefix, sizeof(version_prefix),
				     sizeof(version_reply) - 1) == -1);
	assert(wmt_full_receive_task(&state, wire, bytes, STP_FULL_TASK_BT,
				     version_prefix, sizeof(version_reply) + 1,
				     sizeof(version_reply)) == -1);
	/* The exact WMT wrapper refuses the variable tail. */
	assert(wmt_full_receive(&state, wire, bytes, version_prefix,
				sizeof(version_reply)) == -1);
	assert(!memcmp(&state, &before, sizeof(state)));
	/* Accepted: prefix matches, tail is captured as received. */
	assert(wmt_full_receive_task(&state, wire, bytes, STP_FULL_TASK_BT,
				     version_prefix, sizeof(version_prefix),
				     sizeof(version_reply)) == 1);
	assert(state.event_seen && state.acknowledged && state.transport.ack_owed);
	/* A second copy is a duplicate and is refused by the one-reply client. */
	before = state;
	assert(wmt_full_receive_task(&state, wire, bytes, STP_FULL_TASK_BT,
				     version_prefix, sizeof(version_prefix),
				     sizeof(version_reply)) == -1);
	assert(!memcmp(&state, &before, sizeof(state)));
	assert(wmt_full_ack_sent(&state, 1) == 0 && wmt_full_finish(&state) == 0);
	assert(state.transport.tx_next == 2 && state.transport.rx_next == 2);
	puts("bt-h1 task-0 routing: pass");
	return 0;
}
