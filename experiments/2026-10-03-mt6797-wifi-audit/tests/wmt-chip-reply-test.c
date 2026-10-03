/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-chip-reply.h"

static void le16(unsigned char *out, unsigned int value)
{
	out[0] = (unsigned char)value;
	out[1] = (unsigned char)(value >> 8);
}

int main(int argc, char **argv)
{
	unsigned char frame[64] = { 0 }, changed[64];
	unsigned int i, value, refused = 0;

	/* Construct an independent semantic fixture, not a raw captured log. */
	frame[0] = 0x80; /* measured mandatory-mode sync/sequence byte */
	frame[1] = 0x40; /* WMT service */
	le16(frame + 2, 16); /* complete WMT event size */
	frame[4] = 2; frame[5] = 8;
	le16(frame + 6, 12); /* observed inner length, not vendor template 4 */
	frame[11] = 1; /* single-register count; status/reserved bytes zero */
	frame[12] = 8; frame[15] = 0x80; /* echoed firmware address */
	le16(frame + 16, 0x0279); /* exact observed chip value; high bits zero */
	assert(wmt_chip_reply(frame, 22) == 1);
	for (i = 0; i < 22; i++)
		for (value = 0; value < 256; value++) {
			if (value == frame[i])
				continue;
			memcpy(changed, frame, sizeof(frame));
			changed[i] = (unsigned char)value;
			assert(wmt_chip_reply(changed, 22) == 0);
			refused++;
		}
	for (i = 0; i <= sizeof(frame); i++) {
		if (i == 22)
			continue;
		assert(wmt_chip_reply(frame, i) == 0);
		refused++;
	}
	assert(wmt_chip_reply(NULL, 22) == 0);
	refused++;
	/* Optional private binary input proves the matcher against actual evidence. */
	if (argc == 2) {
		FILE *input = fopen(argv[1], "rb");
		size_t size;

		assert(input);
		size = fread(changed, 1, sizeof(changed), input);
		assert(!ferror(input) && feof(input));
		assert(fclose(input) == 0);
		assert(wmt_chip_reply(changed, (unsigned int)size) == 1);
	} else {
		assert(argc == 1);
	}
	printf("chip reply: one semantic fixture, %u corruption/length/null refusals; no I/O effect\n", refused);
	return 0;
}
