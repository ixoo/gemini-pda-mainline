/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp-stream.h"
#include "wmt-full-stp-state.h"

int main(void)
{
	struct wmt_full_stream stream;
	struct wmt_full_frame result, sentinel;
	struct wmt_full_state state;
	unsigned char frame[WMT_FULL_MAX_FRAME], payload[WMT_FULL_MAX_PAYLOAD];
	static const unsigned char event[] = { 2, 7, 1, 0, 0 };
	unsigned int i, boundary, length;
	static const unsigned int lengths[] = { 1, 5, 10, 255, 256, 1000, 1005 };
	int bytes;

	memset(&sentinel, 0xa5, sizeof(sentinel));
	for (i = 0; i < sizeof(payload); i++)
		payload[i] = i;
	/* Header length boundaries and FIFO-sized input fragments must not expose
	 * a result before the final CRC byte. A caller can pause at every byte.
	 */
	for (boundary = 0; boundary < sizeof(lengths) / sizeof(lengths[0]); boundary++) {
		length = lengths[boundary];
		bytes = wmt_full_encode(frame, sizeof(frame), payload, length, 0, 7);
		wmt_full_stream_init(&stream);
		memcpy(&result, &sentinel, sizeof(result));
		for (i = 0; i < (unsigned int)bytes; i++) {
			assert(wmt_full_stream_byte(&stream, frame[i], &result) ==
			       (i == (unsigned int)bytes - 1 ? 2 : 0));
			if (i < (unsigned int)bytes - 1)
				assert(!memcmp(&result, &sentinel, sizeof(result)));
		}
		assert(result.length == length);
		assert(!memcmp(result.payload, payload, length));
		assert(wmt_full_stream_byte(&stream, 0, &result) == -1);
	}
	/* Oversized lengths refuse at byte four, without collecting any body. */
	for (length = WMT_FULL_MAX_PAYLOAD + 1; length < 4096; length++) {
		frame[0] = 0x80;
		frame[1] = 0x40 | (length >> 8);
		frame[2] = length & 255;
		frame[3] = (frame[0] + frame[1] + frame[2]) & 255;
		wmt_full_stream_init(&stream);
		for (i = 0; i < 4; i++)
			assert(wmt_full_stream_byte(&stream, frame[i], &result) == (i == 3 ? -1 : 0));
		assert(wmt_full_stream_byte(&stream, 0, &result) == -1);
	}
	/* An invalid payload CRC is terminal and cannot be repaired by more bytes. */
	bytes = wmt_full_encode(frame, sizeof(frame), event, sizeof(event), 0, 0);
	frame[bytes - 1] ^= 1;
	wmt_full_stream_init(&stream);
	memcpy(&result, &sentinel, sizeof(result));
	for (i = 0; i < (unsigned int)bytes; i++) {
		assert(wmt_full_stream_byte(&stream, frame[i], &result) ==
		       (i == (unsigned int)bytes - 1 ? -1 : 0));
		assert(!memcmp(&result, &sentinel, sizeof(result)));
	}
	assert(wmt_full_stream_byte(&stream, 0, &result) == -1);
	/* Two frames in one incoming burst still require two explicit acceptance
	 * boundaries: ACK, then exact event, then complete outgoing host ACK.
	 */
	wmt_full_state_init(&state);
	assert(wmt_full_sent(&state, 0) == 0);
	assert(wmt_full_ack(frame, sizeof(frame), 0) == 4);
	wmt_full_stream_init(&stream);
	for (i = 0; i < 4; i++)
		assert(wmt_full_stream_byte(&stream, frame[i], &result) == (i == 3 ? 1 : 0));
	assert(wmt_full_receive(&state, stream.frame, stream.used, event, sizeof(event)) == 0);
	bytes = wmt_full_encode(frame, sizeof(frame), event, sizeof(event), 0, 0);
	wmt_full_stream_init(&stream);
	for (i = 0; i < (unsigned int)bytes; i++)
		assert(wmt_full_stream_byte(&stream, frame[i], &result) ==
		       (i == (unsigned int)bytes - 1 ? 2 : 0));
	assert(wmt_full_receive(&state, stream.frame, stream.used, event, sizeof(event)) == 1);
	assert(wmt_full_finish(&state) == -1);
	assert(wmt_full_ack_sent(&state, 0) == 0);
	assert(wmt_full_finish(&state) == 0);
	puts("full_stp_stream=pass; hardware_actions=none");
	return 0;
}
