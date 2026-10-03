/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp-state.h"

static const unsigned char event[] = { 2, 7, 1, 0, 0 };

int main(void)
{
	struct wmt_full_state state, before;
	unsigned char frame[32], ack[4], wrong[] = { 2, 7, 1, 0, 1 };
	unsigned int command, seq, previous, rx;
	int bytes;

	wmt_full_state_init(&state);
	assert(state.tx_next == 0 && state.rx_next == 0);
	assert(state.peer_ack == 7 && state.local_ack == 7);
	assert(wmt_full_receive(&state, ack, 4, event, sizeof(event)) == -1);
	/* Enough exchanges to cross all modulo-eight boundaries repeatedly during
	 * the retained pair's 258 fragments plus address/reset commands.
	 */
	for (command = 0; command < 264; command++) {
		seq = state.tx_next;
		previous = state.peer_ack;
		rx = state.rx_next;
		before = state;
		assert(wmt_full_sent(&state, (seq + 1) & 7) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		assert(wmt_full_sent(&state, seq) == 0);
		assert(wmt_full_sent(&state, state.tx_next) == -1);
		assert(wmt_full_finish(&state) == -1);
		/* A valid CRC cannot make a wrong event or sequence acceptable. */
		before = state;
		bytes = wmt_full_encode(frame, sizeof(frame), wrong, sizeof(wrong), rx, seq);
		assert(wmt_full_receive(&state, frame, bytes, event, sizeof(event)) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		bytes = wmt_full_encode(frame, sizeof(frame), event, sizeof(event), (rx + 1) & 7, seq);
		assert(wmt_full_receive(&state, frame, bytes, event, sizeof(event)) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		assert(wmt_full_ack(ack, sizeof(ack), (seq + 1) & 7) == 4);
		assert(wmt_full_receive(&state, ack, 4, event, sizeof(event)) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		assert(wmt_full_ack(ack, sizeof(ack), previous) == 4);
		assert(wmt_full_receive(&state, ack, 4, event, sizeof(event)) == 0);
		assert(!memcmp(&state, &before, sizeof(state)));
		bytes = wmt_full_encode(frame, sizeof(frame), event, sizeof(event), rx, seq);
		assert(wmt_full_receive(&state, frame, bytes - 1, event, sizeof(event)) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		assert(wmt_full_receive(&state, frame, bytes, event, sizeof(event) - 1) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		/* Exercise piggyback ACK, separate ACK before event, and late ACK. */
		if (command % 3 == 1) {
			assert(wmt_full_ack(ack, sizeof(ack), seq) == 4);
			assert(wmt_full_receive(&state, ack, 4, event, sizeof(event)) == 0);
			assert(wmt_full_finish(&state) == -1);
		}
		bytes = wmt_full_encode(frame, sizeof(frame), event, sizeof(event), rx,
					command % 3 == 2 ? previous : seq);
		assert(wmt_full_receive(&state, frame, bytes, event, sizeof(event)) == 1);
		assert(state.local_ack == rx && state.rx_next == ((rx + 1) & 7));
		assert(wmt_full_finish(&state) == -1);
		before = state;
		assert(wmt_full_receive(&state, frame, bytes, event, sizeof(event)) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		assert(wmt_full_ack_sent(&state, (rx + 1) & 7) == -1);
		assert(!memcmp(&state, &before, sizeof(state)));
		assert(wmt_full_ack_sent(&state, rx) == 0);
		if (command % 3 == 2) {
			assert(wmt_full_finish(&state) == -1);
			assert(wmt_full_ack(ack, sizeof(ack), seq) == 4);
			assert(wmt_full_receive(&state, ack, 4, event, sizeof(event)) == 0);
		}
		assert(wmt_full_finish(&state) == 0);
		assert(state.tx_next == ((seq + 1) & 7));
		assert(state.peer_ack == seq && !state.active && !state.ack_owed);
	}
	puts("full_stp_single_exchange_state=pass; hardware_actions=none");
	return 0;
}
