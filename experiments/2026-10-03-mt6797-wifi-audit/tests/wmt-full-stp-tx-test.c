/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp-tx.h"
#include "wmt-full-stp-state.h"
#include "wmt-full-stp-stream.h"

int main(void)
{
	unsigned char payload[1005], frame[1011], observed[1011], reply[32];
	static const unsigned char event[] = { 2, 1, 1, 0, 0 };
	const unsigned char *batch = 0;
	struct wmt_full_tx tx, before;
	struct wmt_full_state state;
	struct wmt_full_stream stream;
	struct wmt_full_frame decoded;
	unsigned int i, total, iteration, status;
	int offered, length;

	for (i = 0; i < sizeof(payload); i++)
		payload[i] = i;
	assert(wmt_full_encode(frame, sizeof(frame), payload, sizeof(payload), 0, 7) == 1011);
	wmt_full_state_init(&state);
	assert(wmt_full_tx_init(&tx, frame, sizeof(frame)) == 0);
	total = iteration = 0;
	while (!wmt_full_tx_done(&tx)) {
		/* Fresh observations alternate no room, half-FIFO room and empty FIFO. */
		status = iteration % 3 == 0 ? 0 : iteration % 3 == 1 ? 0x20 : 0x60;
		offered = wmt_full_tx_batch(&tx, status, 0, &batch);
		assert(offered >= 0 && offered <= (status == 0 ? 0 : status == 0x20 ? 8 : 16));
		assert(!state.active && !wmt_full_tx_done(&tx));
		if (offered) {
			memcpy(observed + total, batch, offered);
			total += offered;
			assert(wmt_full_tx_commit(&tx, offered, 0) == 0);
		}
		iteration++;
	}
	assert(total == sizeof(frame) && !memcmp(observed, frame, sizeof(frame)));
	assert(tx.observations == iteration && iteration < WMT_FULL_TX_OBSERVATIONS);
	assert(wmt_full_sent(&state, 0) == 0);
	length = wmt_full_encode(reply, sizeof(reply), event, sizeof(event), 0, 0);
	wmt_full_stream_init(&stream);
	for (i = 0; i < (unsigned int)length; i++)
		assert(wmt_full_stream_byte(&stream, reply[i], &decoded) ==
		       (i == (unsigned int)length - 1 ? 2 : 0));
	assert(wmt_full_receive(&state, stream.frame, stream.used, event, sizeof(event)) == 1);
	assert(wmt_full_finish(&state) == -1);
	assert(wmt_full_ack(reply, sizeof(reply), state.local_ack) == 4);
	assert(wmt_full_tx_init(&tx, reply, 4) == 0);
	assert(wmt_full_tx_batch(&tx, 0x20, 0, &batch) == 4);
	assert(wmt_full_tx_commit(&tx, 4, 0) == 0 && wmt_full_tx_done(&tx));
	assert(wmt_full_ack_sent(&state, state.local_ack) == 0);
	assert(wmt_full_finish(&state) == 0);

	/* Never reuse a room observation while its first batch is uncommitted. */
	assert(wmt_full_tx_init(&tx, frame, sizeof(frame)) == 0);
	assert(wmt_full_tx_batch(&tx, 0x40, 0, &batch) == 16);
	assert(wmt_full_tx_batch(&tx, 0x40, 0, &batch) == -1 && tx.written == 0);
	assert(wmt_full_tx_commit(&tx, 16, 0) == -1 && !wmt_full_tx_done(&tx));
	/* A partial/late write is evidence, never successful submission. */
	assert(wmt_full_tx_init(&tx, frame, sizeof(frame)) == 0);
	assert(wmt_full_tx_batch(&tx, 0x40, 0, &batch) == 16);
	assert(wmt_full_tx_commit(&tx, 7, 0) == -1 && tx.written == 7);
	assert(wmt_full_tx_batch(&tx, 0x40, 0, &batch) == -1);
	assert(wmt_full_tx_init(&tx, reply, 4) == 0);
	assert(wmt_full_tx_batch(&tx, 0x40, 0, &batch) == 4);
	assert(wmt_full_tx_commit(&tx, 4, 1) == -1 && tx.written == 4 && !wmt_full_tx_done(&tx));
	/* Finite no-progress observations and expiry before the first write. */
	assert(wmt_full_tx_init(&tx, frame, sizeof(frame)) == 0);
	for (i = 0; i < WMT_FULL_TX_OBSERVATIONS; i++)
		assert(wmt_full_tx_batch(&tx, 0, 0, &batch) == 0);
	assert(wmt_full_tx_batch(&tx, 0x40, 0, &batch) == -1 && tx.written == 0);
	assert(wmt_full_tx_init(&tx, frame, sizeof(frame)) == 0);
	assert(wmt_full_tx_batch(&tx, 0x40, 1, &batch) == -1 && tx.written == 0);
	memcpy(&before, &tx, sizeof(tx));
	assert(wmt_full_tx_init(&tx, frame, 3) == -1);
	assert(!memcmp(&tx, &before, sizeof(tx)));
	puts("full_stp_tx_progress=pass; hardware_actions=none");
	return 0;
}
