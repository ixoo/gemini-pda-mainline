/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp.h"

int main(void)
{
	/* Golden CRCs independently evaluated with the pinned OSAL lookup table. */
	static const unsigned char query[] = { 1, 4, 1, 0, 4 };
	static const unsigned char encoded[] = {
		0x87, 0x40, 5, 0xcc, 1, 4, 1, 0, 4, 0x6c, 0xf3
	};
	static const unsigned char reply[] = {
		0x80, 0x40, 10, 0xca, 2, 4, 6, 0, 0, 4, 0x11, 0, 0, 0, 0xe7, 0xdc
	};
	unsigned char frame[WMT_FULL_MAX_FRAME + 1], bad[WMT_FULL_MAX_FRAME + 1];
	unsigned char payload[WMT_FULL_MAX_PAYLOAD], alphabet[256];
	struct wmt_full_frame result, sentinel;
	unsigned int i, bit, sequence, acknowledgement;
	int bytes;

	for (i = 0; i < 256; i++)
		alphabet[i] = i;
	assert(wmt_full_crc((const unsigned char *)"123456789", 9) == 0xbb3d);
	assert(wmt_full_crc(alphabet, 256) == 0xbad3);
	assert(wmt_full_crc(query, sizeof(query)) == 0xf36c);
	assert(wmt_full_encode(frame, sizeof(frame), query, sizeof(query), 0, 7) == 11);
	assert(!memcmp(frame, encoded, sizeof(encoded)));
	assert(wmt_full_decode(reply, sizeof(reply), &result) == 1);
	assert(result.sequence == 0 && result.acknowledgement == 0 && result.length == 10);
	assert(result.payload == reply + 4);

	/* Every header/payload/CRC single-bit corruption of the golden reply fails. */
	memset(&sentinel, 0xa5, sizeof(sentinel));
	for (i = 0; i < sizeof(reply); i++) {
		for (bit = 0; bit < 8; bit++) {
			memcpy(bad, reply, sizeof(reply));
			bad[i] ^= 1U << bit;
			memcpy(&result, &sentinel, sizeof(result));
			assert(wmt_full_decode(bad, sizeof(reply), &result) == -1);
			assert(!memcmp(&result, &sentinel, sizeof(result)));
		}
	}
	for (i = 0; i < sizeof(reply); i++)
		assert(wmt_full_decode(reply, i, &result) == -1);
	memcpy(bad, reply, sizeof(reply));
	bad[sizeof(reply)] = 0;
	assert(wmt_full_decode(bad, sizeof(reply) + 1, &result) == -1);

	for (sequence = 0; sequence < 8; sequence++) {
		for (acknowledgement = 0; acknowledgement < 8; acknowledgement++) {
			bytes = wmt_full_encode(frame, sizeof(frame), query, sizeof(query),
						sequence, acknowledgement);
			assert(bytes == 11);
			assert(wmt_full_decode(frame, bytes, &result) == 1);
			assert(result.sequence == sequence && result.acknowledgement == acknowledgement);
			assert(!memcmp(result.payload, query, sizeof(query)));
		}
	}
	for (acknowledgement = 0; acknowledgement < 8; acknowledgement++) {
		assert(wmt_full_ack(frame, sizeof(frame), acknowledgement) == 4);
		assert(wmt_full_decode(frame, 4, &result) == 0);
		assert(result.sequence == 0 && result.acknowledgement == acknowledgement);
		assert(result.length == 0 && !result.payload);
		assert(wmt_full_decode(frame, 5, &result) == -1);
	}

	for (i = 0; i < sizeof(payload); i++)
		payload[i] = i;
	assert(wmt_full_crc(payload, sizeof(payload)) == 0xc159);
	bytes = wmt_full_encode(frame, sizeof(frame), payload, sizeof(payload), 7, 7);
	assert(bytes == WMT_FULL_MAX_FRAME);
	assert(wmt_full_decode(frame, bytes, &result) == 1);
	assert(result.length == sizeof(payload));
	assert(!memcmp(result.payload, payload, sizeof(payload)));
	/* Valid checksum cannot make an oversized or unselected-task frame valid. */
	frame[1] = 0x44;
	frame[2] = 0;
	frame[3] = (frame[0] + frame[1] + frame[2]) & 255;
	assert(wmt_full_decode(frame, bytes, &result) == -1);
	memcpy(frame, reply, sizeof(reply));
	frame[1] = 0x50;
	frame[3] = (frame[0] + frame[1] + frame[2]) & 255;
	assert(wmt_full_decode(frame, sizeof(reply), &result) == -1);


	/* Refuse unsupported flags even when the header checksum is recomputed. */
	memcpy(frame, reply, sizeof(reply));
	frame[1] |= 0x80;
	frame[3] = (frame[0] + frame[1] + frame[2]) & 255;
	assert(wmt_full_decode(frame, sizeof(reply), &result) == -1);
	assert(wmt_full_ack(frame, sizeof(frame), 0) == 4);
	frame[1] = 0x40;
	frame[3] = (frame[0] + frame[1] + frame[2]) & 255;
	assert(wmt_full_decode(frame, 4, &result) == -1);

	memset(frame, 0xa5, sizeof(frame));
	memcpy(bad, frame, sizeof(frame));
	assert(wmt_full_encode(frame, 10, query, 5, 0, 7) == -1);
	assert(wmt_full_encode(frame, sizeof(frame), payload, sizeof(payload) + 1, 0, 7) == -1);
	assert(wmt_full_encode(frame, sizeof(frame), query, 5, 8, 7) == -1);
	assert(wmt_full_encode(frame, sizeof(frame), query, 5, 0, 8) == -1);
	assert(wmt_full_encode(frame, sizeof(frame), query, 0, 0, 7) == -1);
	assert(wmt_full_encode(frame, sizeof(frame), 0, 5, 0, 7) == -1);
	assert(wmt_full_encode(0, sizeof(frame), query, 5, 0, 7) == -1);
	assert(wmt_full_ack(frame, 3, 0) == -1);
	assert(wmt_full_ack(frame, sizeof(frame), 8) == -1);
	assert(!memcmp(frame, bad, sizeof(frame)));
	assert(wmt_full_decode(0, 4, &result) == -1);
	assert(wmt_full_decode(reply, sizeof(reply), 0) == -1);
	puts("full_stp_codec=pass; hardware_actions=none");
	return 0;
}
