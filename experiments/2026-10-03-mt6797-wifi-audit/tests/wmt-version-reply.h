/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_VERSION_REPLY_H
#define GEMINI_WMT_VERSION_REPLY_H

/* Chip format/value are measured. HW/ROM use the same read-event contract
 * with their echoed addresses and the vendor-reported 0x8a00 expectations.
 * Those two variants remain inference until attributable live exchanges.
 * Never accept another tuple, length, status, count or mandatory header.
 */
static inline int wmt_version_reply(unsigned int ordinal,
				    const unsigned char *wire, unsigned int length)
{
	static const unsigned char offsets[3] = { 8, 0, 4 };
	static const unsigned char values[3][2] = { { 0x79, 0x02 },
		{ 0x00, 0x8a }, { 0x00, 0x8a } };
	static const unsigned char frame[22] = {
		0x80, 0x40, 0x10, 0x00,
		0x02, 0x08, 0x0c, 0x00, 0x00, 0x00, 0x00, 0x01,
		0x00, 0x00, 0x00, 0x80,
		0x00, 0x00, 0x00, 0x00,
		0x00, 0x00
	};
	unsigned int i;
	unsigned char expected;

	if (ordinal >= 3 || !wire || length != sizeof(frame))
		return 0;
	for (i = 0; i < sizeof(frame); i++) {
		expected = i == 12 ? offsets[ordinal] :
			   i == 16 ? values[ordinal][0] :
			   i == 17 ? values[ordinal][1] : frame[i];
		if (wire[i] != expected)
			return 0;
	}
	return 1;
}

#endif
