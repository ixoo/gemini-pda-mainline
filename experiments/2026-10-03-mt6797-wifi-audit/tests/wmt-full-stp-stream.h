/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_FULL_STP_STREAM_H
#define GEMINI_WMT_FULL_STP_STREAM_H
#include "wmt-full-stp.h"

/* Persistent caller storage; decoded payload aliases this buffer. Consume the
 * completed frame before initializing for the next frame. No resynchronization.
 */
struct wmt_full_stream {
	unsigned char frame[WMT_FULL_MAX_FRAME];
	unsigned int used, needed;
	int terminal;
};

static inline void wmt_full_stream_init(struct wmt_full_stream *stream)
{
	stream->used = 0;
	stream->needed = 4;
	stream->terminal = 0;
}

/* 0: incomplete, 1: ACK, 2: data, -1: terminal refusal. The owner also limits
 * aggregate bytes, frame count, IRQ work and elapsed time across exchanges.
 */
static inline int wmt_full_stream_byte(struct wmt_full_stream *stream,
		unsigned char byte, struct wmt_full_frame *result)
{
	unsigned int length;
	int kind;

	if (!stream || !result)
		return -1;
	if (stream->terminal || stream->used >= sizeof(stream->frame))
		goto refuse;
	stream->frame[stream->used++] = byte;
	if (stream->used == 4) {
		const unsigned char *h = stream->frame;

		length = ((h[1] & 15) << 8) | h[2];
		if ((h[0] & 0xc0) != 0x80 || (h[1] & 0x80) ||
		    ((h[0] + h[1] + h[2]) & 255) != h[3] ||
		    length > WMT_FULL_MAX_PAYLOAD ||
		    (!length && h[1]) || (length && (h[1] & 0x70) != 0x40))
			goto refuse;
		stream->needed = length ? length + 6 : 4;
	}
	if (stream->used < stream->needed)
		return 0;
	kind = wmt_full_decode(stream->frame, stream->used, result);
	if (kind < 0)
		goto refuse;
	stream->terminal = 1;
	return kind + 1;
refuse:
	stream->terminal = -1;
	return -1;
}
#endif
