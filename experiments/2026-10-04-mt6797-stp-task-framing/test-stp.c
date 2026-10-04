/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "stp-full-stream.h"
#include "wmt-full-stp.h"

int main(void)
{
	/* Payload CRCs independently evaluated with pinned Linux crc16_table. */
	static const unsigned char reset[] = { 1, 3, 12, 0 };
	static const unsigned char reset_wire[] = {
		0x87, 0, 4, 0x8b, 1, 3, 12, 0, 0xf4, 0xfc
	};
	static const unsigned char complete[] = {
		0x80, 0, 7, 0x87, 4, 14, 4, 1, 3, 12, 0, 0x41, 0xd2
	};
	static const unsigned int tasks[] = { 0, 1, 2, 3, 4, 7 };
	unsigned char frame[STP_FULL_MAX_FRAME + 1], saved[STP_FULL_MAX_FRAME + 1];
	unsigned char payload[STP_FULL_MAX_PAYLOAD];
	struct stp_full_frame result, sentinel;
	struct wmt_full_frame wmt, wmt_sentinel;
	struct stp_full_stream stream;
	unsigned int i, j, bit, task, seq, ack;
	int bytes, parsed;

	assert(stp_full_crc(reset, sizeof(reset)) == 0xfcf4);
	assert(stp_full_encode(frame, sizeof(frame), reset, sizeof(reset), 0, 0, 7)
	       == sizeof(reset_wire));
	assert(!memcmp(frame, reset_wire, sizeof(reset_wire)));
	assert(stp_full_decode(complete, sizeof(complete), &result) == 1);
	assert(result.task == STP_FULL_TASK_BT && result.length == 7);
	assert(result.payload == complete + 4);
	memset(&sentinel, 0xa5, sizeof(sentinel));
	memset(&wmt_sentinel, 0xa5, sizeof(wmt_sentinel));
	memcpy(&wmt, &wmt_sentinel, sizeof(wmt));
	assert(wmt_full_decode(complete, sizeof(complete), &wmt) == -1);
	assert(!memcmp(&wmt, &wmt_sentinel, sizeof(wmt)));

	for (i = 0; i < sizeof(complete); i++) {
		memcpy(&result, &sentinel, sizeof(result));
		assert(stp_full_decode(complete, i, &result) == -1);
		assert(!memcmp(&result, &sentinel, sizeof(result)));
		for (bit = 0; bit < 8; bit++) {
			memcpy(frame, complete, sizeof(complete));
			frame[i] ^= 1U << bit;
			assert(stp_full_decode(frame, sizeof(complete), &result) == -1);
			assert(!memcmp(&result, &sentinel, sizeof(result)));
		}
	}
	memcpy(frame, complete, sizeof(complete));
	frame[sizeof(complete)] = 0;
	assert(stp_full_decode(frame, sizeof(complete) + 1, &result) == -1);
	for (i = 0; i < sizeof(tasks) / sizeof(tasks[0]); i++) {
		task = tasks[i];
		for (seq = 0; seq < 8; seq++) {
			for (ack = 0; ack < 8; ack++) {
				bytes = stp_full_encode(frame, sizeof(frame), reset,
						 sizeof(reset), task, seq, ack);
				assert(bytes == sizeof(reset_wire));
				assert(stp_full_decode(frame, bytes, &result) == 1);
				assert(result.task == task && result.sequence == seq &&
				       result.acknowledgement == ack);
				assert(!memcmp(result.payload, reset, sizeof(reset)));
			}
		}
	}
	for (i = 0; i < sizeof(payload); i++)
		payload[i] = i;
	assert(stp_full_crc(payload, sizeof(payload)) == 0xd7dd);
	bytes = stp_full_encode(frame, sizeof(frame), payload, sizeof(payload), 0, 7, 7);
	assert(bytes == STP_FULL_MAX_FRAME);
	assert(stp_full_decode(frame, bytes, &result) == 1);
	assert(result.length == STP_FULL_MAX_PAYLOAD);
	assert(wmt_full_encode(saved, sizeof(saved), payload, 1006, 0, 7) == -1);
	bytes = stp_full_encode(frame, sizeof(frame), payload, 1006, 4, 0, 7);
	assert(bytes == 1012 && wmt_full_decode(frame, bytes, &wmt) == -1);
	memset(frame, 0xa5, sizeof(frame));
	memcpy(saved, frame, sizeof(frame));
	for (i = 5; i < 10; i++) {
		if (i == 7)
			continue;
		assert(stp_full_encode(frame, sizeof(frame), reset, sizeof(reset), i, 0, 7)
		       == -1);
		assert(!memcmp(frame, saved, sizeof(frame)));
	}
	assert(stp_full_encode(frame, sizeof(frame), payload, 2049, 0, 0, 7) == -1);
	assert(!memcmp(frame, saved, sizeof(frame)));
	assert(stp_full_encode(frame, 9, reset, sizeof(reset), 0, 0, 7) == -1);
	assert(stp_full_encode(frame, sizeof(frame), reset, 0, 0, 0, 7) == -1);
	assert(stp_full_encode(frame, sizeof(frame), reset, 4, 0, 8, 7) == -1);
	assert(stp_full_encode(frame, sizeof(frame), reset, 4, 0, 0, 8) == -1);
	assert(!memcmp(frame, saved, sizeof(frame)));
	for (i = 0; i < 8; i++) {
		assert(stp_full_ack(frame, sizeof(frame), i) == 4);
		assert(stp_full_decode(frame, 4, &result) == 0);
		assert(result.task == STP_FULL_TASK_NONE && !result.payload);
		assert(result.acknowledgement == i);
	}
	/* Header flags, special task framing and >2048 all fail at the header. */
	for (i = 0; i < 4; i++) {
		memcpy(frame, complete, sizeof(complete));
		frame[1] = i == 0 ? 0x80 : i == 1 ? 0x50 : i == 2 ? 0x60 : 0x08;
		if (i == 3)
			frame[2] = 1;
		frame[3] = (frame[0] + frame[1] + frame[2]) & 255;
		memcpy(&result, &sentinel, sizeof(result));
		assert(stp_full_decode(frame, sizeof(complete), &result) == -1);
		assert(!memcmp(&result, &sentinel, sizeof(result)));
	}
	/* Persistent byte parsing exposes data only after the final CRC byte. */
	stp_full_stream_init(&stream);
	memcpy(&result, &sentinel, sizeof(result));
	for (j = 0; j < sizeof(complete); j++) {
		parsed = stp_full_stream_byte(&stream, complete[j], &result);
		assert(parsed == (j + 1 == sizeof(complete) ? 2 : 0));
		if (!parsed)
			assert(!memcmp(&result, &sentinel, sizeof(result)));
	}
	assert(result.task == 0 && result.length == 7);
	assert(stp_full_stream_byte(&stream, 0, &result) == -1);
	/* Maximum payload fits persistent storage; corruption is terminal. */
	bytes = stp_full_encode(frame, sizeof(frame), payload, sizeof(payload), 0, 7, 7);
	for (i = 0; i < 2; i++) {
		stp_full_stream_init(&stream);
		memcpy(&result, &sentinel, sizeof(result));
		if (i)
			frame[bytes - 1] ^= 1;
		for (j = 0; j < (unsigned int)bytes; j++) {
			parsed = stp_full_stream_byte(&stream, frame[j], &result);
			assert(parsed == (j + 1 == (unsigned int)bytes ? (i ? -1 : 2) : 0));
			if (parsed != 2)
				assert(!memcmp(&result, &sentinel, sizeof(result)));
		}
		if (!i)
			assert(!memcmp(result.payload, payload, sizeof(payload)));
		assert(stp_full_stream_byte(&stream, 0, &result) == -1);
	}
	for (i = 0; i < sizeof(tasks) / sizeof(tasks[0]); i++) {
		bytes = stp_full_encode(frame, sizeof(frame), reset, sizeof(reset), tasks[i], i, 7);
		stp_full_stream_init(&stream);
		for (j = 0; j < (unsigned int)bytes; j++)
			assert(stp_full_stream_byte(&stream, frame[j], &result) ==
			       (j + 1 == (unsigned int)bytes ? 2 : 0));
		assert(result.task == tasks[i] && result.sequence == i);
	}
	puts("stp_task_framing=pass; WMT compatibility retained; no device access");
	return 0;
}
