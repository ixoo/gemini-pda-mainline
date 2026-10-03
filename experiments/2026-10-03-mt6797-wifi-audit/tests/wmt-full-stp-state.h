/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_FULL_STP_STATE_H
#define GEMINI_WMT_FULL_STP_STATE_H
#include "wmt-full-stp.h"

/* Single-owner, one-command window. Initialize only at an admitted full-mode
 * boundary, never because an ordinary WMT reset event was received.
 */
struct wmt_full_state {
	unsigned int tx_next, rx_next, peer_ack, local_ack;
	unsigned int active, sent_sequence, acknowledged, event_seen, ack_owed;
};

static inline void wmt_full_state_init(struct wmt_full_state *state)
{
	struct wmt_full_state initial = { .peer_ack = 7, .local_ack = 7 };

	*state = initial;
}

/* Call only after all encoded command bytes were transmitted successfully.
 * A partial TX must retire the caller's lifetime without this transition.
 */
static inline int wmt_full_sent(struct wmt_full_state *state, unsigned int sequence)
{
	if (!state || state->active || sequence != state->tx_next)
		return -1;
	state->active = 1;
	state->sent_sequence = sequence;
	state->tx_next = (sequence + 1) & 7;
	state->acknowledged = 0;
	state->event_seen = 0;
	return 0;
}

/* Exact event comparison precedes all state mutation. An ACK can precede or
 * follow the event, or be piggybacked on it. Repeated previous ACKs consume no
 * credit; caller bounds total frames/time and retires on every refusal.
 */
static inline int wmt_full_receive(struct wmt_full_state *state,
		const unsigned char *frame, unsigned int bytes,
		const unsigned char *expected, unsigned int expected_length)
{
	struct wmt_full_frame decoded;
	unsigned int i;
	int kind;

	if (!state || !state->active)
		return -1;
	kind = wmt_full_decode(frame, bytes, &decoded);
	if (kind < 0 || (decoded.acknowledgement != state->peer_ack &&
			decoded.acknowledgement != state->sent_sequence))
		return -1;
	if (kind) {
		if (!expected || state->event_seen || decoded.sequence != state->rx_next ||
		    decoded.length != expected_length)
			return -1;
		for (i = 0; i < expected_length; i++)
			if (decoded.payload[i] != expected[i])
				return -1;
	}
	if (decoded.acknowledgement == state->sent_sequence) {
		state->peer_ack = decoded.acknowledgement;
		state->acknowledged = 1;
	}
	if (kind) {
		state->local_ack = decoded.sequence;
		state->rx_next = (decoded.sequence + 1) & 7;
		state->event_seen = 1;
		state->ack_owed = 1;
	}
	return kind;
}

/* Call only after the four-byte host ACK was transmitted completely. */
static inline int wmt_full_ack_sent(struct wmt_full_state *state, unsigned int ack)
{
	if (!state || !state->active || !state->ack_owed || ack != state->local_ack)
		return -1;
	state->ack_owed = 0;
	return 0;
}

static inline int wmt_full_finish(struct wmt_full_state *state)
{
	if (!state || !state->active || !state->acknowledged ||
	    !state->event_seen || state->ack_owed)
		return -1;
	state->active = 0;
	return 0;
}
#endif
