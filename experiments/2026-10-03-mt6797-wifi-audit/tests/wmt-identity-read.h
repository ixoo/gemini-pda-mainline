/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_IDENTITY_READ_H
#define GEMINI_WMT_IDENTITY_READ_H

/* Construct only the three selected pre-negotiation mandatory-STP reads,
 * ordered chip, HW, ROM. No reply acceptance, I/O or identity selection.
 * Refusal leaves output unchanged. No caller-supplied register or write op.
 */
static inline int wmt_identity_read(unsigned int ordinal, unsigned char *out,
				    unsigned int capacity)
{
	static const unsigned char offsets[3] = { 8, 0, 4 };
	static const unsigned char frame[26] = {
		0x80, 0x40, 0x14, 0x00,
		0x01, 0x08, 0x10, 0x00, 0x02, 0x01, 0x00, 0x01,
		0x00, 0x00, 0x00, 0x80,
		0x00, 0x00, 0x00, 0x00,
		0xff, 0xff, 0x00, 0x00,
		0x00, 0x00
	};
	unsigned int i;

	if (ordinal >= 3 || !out || capacity < sizeof(frame))
		return -1;
	for (i = 0; i < sizeof(frame); i++)
		out[i] = frame[i];
	out[12] = offsets[ordinal];
	return sizeof(frame);
}

#endif
