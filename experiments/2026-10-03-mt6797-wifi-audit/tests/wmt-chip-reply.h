/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_CHIP_REPLY_H
#define GEMINI_WMT_CHIP_REPLY_H

/* Accept only the measured pre-patch mandatory-mode chip reply for 0x0279.
 * No HW/ROM inference, applicability selection, I/O, resync or continuation.
 * The complete caller-owned capture must be supplied, with no trailing bytes.
 */
static inline int wmt_chip_reply(const unsigned char *wire, unsigned int length)
{
	static const unsigned char expected[22] = {
		0x80, 0x40, 0x10, 0x00,
		0x02, 0x08, 0x0c, 0x00, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x00, 0x00, 0x80,
		0x79, 0x02, 0x00, 0x00,
		0x00, 0x00
	};
	unsigned int i;

	if (!wire || length != sizeof(expected))
		return 0;
	for (i = 0; i < sizeof(expected); i++)
		if (wire[i] != expected[i])
			return 0;
	return 1;
}

#endif
