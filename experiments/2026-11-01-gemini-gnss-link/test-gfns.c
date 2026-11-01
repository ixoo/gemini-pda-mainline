/* SPDX-License-Identifier: GPL-2.0-only */
/* GFNS receive parser against the actual header. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mt6797-gfns.h"

static struct gfns_rx rx;

static unsigned int feed(const unsigned char *bytes, unsigned int n, struct gfns_frame *out,
			 unsigned char *copy)
{
	struct gfns_frame f;
	unsigned int i, frames = 0;

	for (i = 0; i < n; i++) {
		if (!gfns_rx_byte(&rx, bytes[i], &f))
			continue;
		frames++;
		*out = f;
		if (copy)
			memcpy(copy, f.payload, f.length);
	}
	return frames;
}

int main(void)
{
	/* The record's keep-alive frame, as the host builds it. */
	static const unsigned char keepalive[] = {
		0xa5, 0x00, 0x76, 0x00, 0x04, 0x7a, 1, 2, 3, 4, 0xa3,
	};
	/* The checksum covers the channel byte, as the vendor receiver reads it. */
	static const unsigned char nmea[] = {
		0xa5, 0x40, 0x0a, 0x00, 0x03, 0x4d, '$', 'G', 'P', 0xa3,
	};
	static const unsigned char bad_sum[] = {
		0xa5, 0x40, 0x0a, 0x00, 0x03, 0x4e, '$', 'G', 'P', 0xa3,
	};
	static const unsigned char no_end[] = {
		0xa5, 0x00, 0x0b, 0x00, 0x01, 0x0c, 'x', 0x00,
	};
	static const unsigned char empty[] = { 0xa5, 0x00, 0x13, 0x00, 0x00, 0x13, 0xa3 };
	/* Length 0x0801 is one past the limit; the sum is right. */
	static const unsigned char huge[] = { 0xa5, 0x00, 0x0a, 0x08, 0x01, 0x13 };
	static const unsigned char inner[] = {
		0xa5, 0x00, 0x0a, 0x00, 0x02, 0x0c, 0xa5, 0xa3, 0xa3,
	};
	static unsigned char largest[GFNS_HEADER + GFNS_MAX_PAYLOAD + 1], copy[GFNS_MAX_PAYLOAD];
	struct gfns_frame f;
	unsigned int chunk, i, frames;

	gfns_rx_init(&rx);
	assert(feed(keepalive, sizeof(keepalive), &f, NULL) == 1);
	assert(f.type == 0x76 && f.channel == 0 && f.length == 4 && f.payload[3] == 4);

	assert(feed(nmea, sizeof(nmea), &f, copy) == 1);
	assert(f.type == GFNS_RSP_NMEA && f.channel == 2 && f.length == 3);
	assert(!memcmp(copy, "$GP", 3));

	assert(feed(empty, sizeof(empty), &f, NULL) == 1);
	assert(f.type == 0x13 && f.length == 0 && !rx.bad);

	/* A frame split at every chunk size arrives once, unchanged. */
	for (chunk = 1; chunk <= sizeof(nmea); chunk++) {
		frames = 0;
		for (i = 0; i < sizeof(nmea); i += chunk)
			frames += feed(nmea + i, i + chunk > sizeof(nmea) ?
				       sizeof(nmea) - i : chunk, &f, copy);
		assert(frames == 1 && f.length == 3 && !memcmp(copy, "$GP", 3));
	}

	/* Bytes between frames are skipped silently. */
	assert(feed((const unsigned char *)"\x00\x11\x22", 3, &f, NULL) == 0 && !rx.bad);
	assert(feed(nmea, sizeof(nmea), &f, NULL) == 1);

	/* A start byte and an end byte inside a payload are payload. */
	assert(feed(inner, sizeof(inner), &f, copy) == 1);
	assert(f.length == 2 && copy[0] == 0xa5 && copy[1] == 0xa3);

	/* The largest frame is accepted. */
	memset(largest, 0x5a, sizeof(largest));
	largest[0] = 0xa5;
	largest[1] = 0;
	largest[2] = 0x0a;
	largest[3] = GFNS_MAX_PAYLOAD >> 8;
	largest[4] = GFNS_MAX_PAYLOAD & 0xff;
	largest[5] = (0x0a + largest[3] + largest[4]) & 0xff;
	largest[sizeof(largest) - 1] = 0xa3;
	assert(feed(largest, sizeof(largest), &f, copy) == 1);
	assert(f.length == GFNS_MAX_PAYLOAD && copy[GFNS_MAX_PAYLOAD - 1] == 0x5a);

	/* Each refusal is counted, and the next good frame still arrives. */
	gfns_rx_init(&rx);
	assert(feed(bad_sum, sizeof(bad_sum), &f, NULL) == 0 && rx.bad == 1);
	assert(feed(nmea, sizeof(nmea), &f, NULL) == 1);
	assert(feed(no_end, sizeof(no_end), &f, NULL) == 0 && rx.bad == 2);
	assert(feed(nmea, sizeof(nmea), &f, NULL) == 1);
	assert(feed(huge, sizeof(huge), &f, NULL) == 0 && rx.bad == 3);
	assert(feed(nmea, sizeof(nmea), &f, NULL) == 1);

	/* A checksum that fails on a start byte keeps it as the next frame's start. */
	gfns_rx_init(&rx);
	assert(feed((const unsigned char *)"\xa5\x00\x00\x00\x01\xa5", 6, &f, NULL) == 0);
	assert(rx.bad == 1 && rx.used == 1);
	assert(feed(nmea + 1, sizeof(nmea) - 1, &f, NULL) == 1);

	/* Transmit: the record's keep-alive bytes, and an empty frame. */
	{
		static const unsigned char counter[] = { 1, 2, 3, 4 };
		unsigned char out[32], ack[GFNS_ACK_BYTES], utc[12];

		assert(gfns_encode(out, sizeof(out), GFNS_REQ_KEEP_ALIVE, counter, 4) ==
		       sizeof(keepalive));
		assert(!memcmp(out, keepalive, sizeof(keepalive)));
		assert(gfns_encode(out, sizeof(out), GFNS_REQ_MNL_INIT_CFG, NULL, 0) == 7);
		assert(out[2] == 0x14 && out[5] == 0x14 && out[6] == 0xa3);
		assert(gfns_encode(out, 6, GFNS_REQ_STOP, NULL, 0) == 0);

		/* What we send, the parser accepts. */
		gfns_rx_init(&rx);
		assert(feed(out, 7, &f, NULL) == 1 && f.type == 0x14 && !f.length);

		/* Received 0x12345 bytes: low 16 bits, then multiples of 0x10000. */
		gfns_ack(ack, 0x12345, 7, 8, 9);
		assert(gfns_get32(ack) == 0x2345 && gfns_get32(ack + 4) == 1);
		assert(gfns_get32(ack + 8) == 7 && gfns_get32(ack + 12) == 8);
		assert(gfns_get32(ack + 16) == 0 && gfns_get32(ack + 20) == 9);
		assert(gfns_get32(ack + 24) == 0x10);

		/* 1 November 2026, 13:05:09 UTC. */
		gfns_utc(utc, 126, 10, 1, 13, 5, 9);
		assert(utc[0] == 126 && utc[1] == 0 && utc[2] == 10 && utc[3] == 1);
		assert(utc[4] == 13 && utc[5] == 5 && utc[6] == 9 && !utc[7] && !utc[11]);
	}

	/* The start configuration, against mnld's field layout. */
	{
		unsigned char cfg[GFNS_CFG_BYTES], out[GFNS_CFG_BYTES + GFNS_OVERHEAD];

		gfns_cfg(cfg);
		assert(cfg[0] == 1 && cfg[3] == 2 && cfg[5] == 100 && cfg[8] == 0xff);
		assert(cfg[9] == 0xd0 && cfg[10] == 0x07);
		assert(gfns_get32(cfg + 11) == 26000000 && gfns_get32(cfg + 15) == 115200);
		assert(gfns_get32(cfg + 19) == 1000 && gfns_get32(cfg + 24) == 0x800000f0);
		assert(gfns_get32(cfg + 28) == 0xffff6797 && cfg[32] == 2);
		for (i = 33; i < GFNS_CFG_BYTES; i++)
			assert(!cfg[i]);
		assert(gfns_encode(out, sizeof(out), GFNS_REQ_MNL_INIT_CFG, cfg, sizeof(cfg)) ==
		       sizeof(out));
		assert(out[2] == 0x14 && out[4] == 49 && out[5] == 0x45);
	}

	/* Refused bytes are counted, and a start byte kept for the next frame is not. */
	gfns_rx_init(&rx);
	assert(feed(bad_sum, 6, &f, NULL) == 0 && rx.dropped == 6);
	gfns_rx_init(&rx);
	assert(feed((const unsigned char *)"\xa5\x00\x00\x00\x01\xa5", 6, &f, NULL) == 0);
	assert(rx.dropped == 5 && rx.used == 1);

	puts("gfns: framing, channel, checksum, bounds, refusal, restart and transmit pass");
	return 0;
}
