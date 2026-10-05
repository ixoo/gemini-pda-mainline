/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * The RF calibration event carries firmware-defined calibration data. Runtime 2
 * received a 378-byte body; the exact-length matcher refused it. Feed framed
 * events through the real receive path with synthetic data only.
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp-state.h"

static const unsigned char prefix[] = { 0x02, 0x14 };

/* Encode one task-4 data frame holding a WMT event and offer it to a fresh link. */
static int offer(unsigned int body, int length_field_delta, unsigned char opcode,
		 unsigned int expected_length)
{
	unsigned char event[WMT_FULL_MAX_PAYLOAD], frame[WMT_FULL_MAX_FRAME];
	struct wmt_full_state state;
	unsigned int i, field = body + length_field_delta;
	int bytes, kind;

	assert(body + 4 <= sizeof(event));
	event[0] = 0x02;
	event[1] = opcode;
	event[2] = field & 255;
	event[3] = field >> 8;
	for (i = 0; i < body; i++)
		event[4 + i] = (unsigned char)(0x5a ^ i);
	wmt_full_state_init(&state);
	assert(!wmt_full_sent(&state, 0));
	bytes = stp_full_encode(frame, sizeof(frame), event, body + 4,
				STP_FULL_TASK_WMT, 0, 0);
	assert(bytes == (int)body + 10);
	kind = wmt_full_receive_task(&state, frame, bytes, STP_FULL_TASK_WMT, prefix,
				     sizeof(prefix), expected_length);
	if (kind > 0)
		assert(state.event_seen && state.transport.ack_owed);
	else
		assert(!state.event_seen);
	return kind;
}

int main(void)
{
	/* Runtime 2 shape: 378-byte body, 382-byte event, 392 bytes with an ACK. */
	assert(offer(378, 0, 0x14, 0) == 1);
	/* The vendor's documented 2-byte form and the largest frame also pass. */
	assert(offer(2, 0, 0x14, 0) == 1);
	assert(offer(WMT_FULL_MAX_PAYLOAD - 4, 0, 0x14, 0) == 1);
	/* Inconsistent length field, wrong opcode or a header-only event refuse. */
	assert(offer(378, 1, 0x14, 0) < 0);
	assert(offer(378, -1, 0x14, 0) < 0);
	assert(offer(378, 0, 0x10, 0) < 0);
	assert(offer(0, 0, 0x14, 0) == 1);
	/* The old exact contract refused runtime 2's event and still refuses it. */
	assert(offer(378, 0, 0x14, 6) < 0);
	assert(offer(2, 0, 0x14, 6) == 1);
	puts("calibration event: variable body accepted with exact length field; mismatches refused");
	return 0;
}
