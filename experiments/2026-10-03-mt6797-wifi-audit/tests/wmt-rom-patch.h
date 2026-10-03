/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_WMT_ROM_PATCH_H
#define GEMINI_WMT_ROM_PATCH_H

struct wmt_rom_patch {
	const unsigned char *body;
	unsigned int length, sequence;
	unsigned char address[4];
};

/* Selected retained pair only. Caller verifies exact full-file digest and
 * applicability separately; metadata alone is not firmware authentication.
 * Result aliases immutable input. Refusal leaves output unchanged.
 */
static inline int wmt_rom_patch_parse(const unsigned char *file, unsigned int bytes,
		unsigned int sequence, struct wmt_rom_patch *result)
{
	static const unsigned int lengths[] = { 46444, 210876 };
	static const unsigned char addresses[][4] = {
		{ 0, 0, 0x0a, 0xf0 }, { 0, 0, 9, 0 }
	};
	unsigned int i;

	if (!file || !result || sequence < 1 || sequence > 2 ||
	    bytes != lengths[sequence - 1] + 28 || file[24] != (0x20 | sequence))
		return -1;
	for (i = 1; i < 4; i++)
		if (file[24 + i] != addresses[sequence - 1][i])
			return -1;
	result->body = file + 28;
	result->length = bytes - 28;
	result->sequence = sequence;
	for (i = 0; i < 4; i++)
		result->address[i] = addresses[sequence - 1][i];
	return 0;
}

/* Construct one WMT payload, not an STP frame or a transfer. Input/output must
 * be disjoint. Index is zero-based; caller advances only after checked event.
 */
static inline int wmt_rom_patch_fragment(const struct wmt_rom_patch *patch,
		unsigned int index, unsigned char *out, unsigned int capacity)
{
	unsigned int count, offset, length, i;

	if (!patch || !patch->body || !patch->length || patch->length > 210876 || !out)
		return -1;
	count = (patch->length + 999) / 1000;
	if (index >= count)
		return -1;
	offset = index * 1000;
	length = patch->length - offset;
	if (length > 1000)
		length = 1000;
	if (capacity < length + 5)
		return -1;
	out[0] = 1;
	out[1] = 1;
	out[2] = (length + 1) & 255;
	out[3] = (length + 1) >> 8;
	out[4] = index == count - 1 ? 3 : index == 0 ? 1 : 2;
	for (i = 0; i < length; i++)
		out[5 + i] = patch->body[offset + i];
	return length + 5;
}
/* MT6797 selected pair: two addresses, body fragments, ordinary WMT reset,
 * then the second patch. Constructor only; ordinal advances after a complete
 * checked transport exchange, never on construction or partial submission.
 * Caller supplies disjoint immutable inputs and separate command/event output.
 */
static inline int mt6797_wmt_rom_step(const struct wmt_rom_patch pair[2],
		unsigned int ordinal, unsigned char *out, unsigned int capacity,
		unsigned char expected[8], unsigned int *expected_length)
{
	static const unsigned int lengths[2] = { 46444, 210876 };
	static const unsigned char addresses[2][4] = {
		{ 0, 0, 10, 240 }, { 0, 0, 9, 0 }
	};
	unsigned int i, j, sequence, step, count, bytes, event_bytes;

	if (!pair || !out || !expected || !expected_length || ordinal >= 264)
		return -1;
	for (i = 0; i < 2; i++) {
		if (!pair[i].body || pair[i].sequence != i + 1 ||
		    pair[i].length != lengths[i])
			return -1;
		for (j = 0; j < 4; j++)
			if (pair[i].address[j] != addresses[i][j])
				return -1;
	}
	sequence = ordinal < 50 ? 0 : 1;
	step = sequence ? ordinal - 50 : ordinal;
	count = (lengths[sequence] + 999) / 1000;
	if (step < 2) {
		if (capacity < 20)
			return -1;
		/* Opcode 8, one masked firmware register operation. */
		out[0] = 1;
		out[1] = 8;
		out[2] = 16;
		out[3] = 0;
		out[4] = 1;
		out[5] = 1;
		out[6] = 0;
		out[7] = 1;
		out[8] = step ? 0x2c : 8;
		out[9] = step ? 0x0b : 5;
		out[10] = 9;
		out[11] = 2;
		for (i = 0; i < 4; i++) {
			out[12 + i] = step ? pair[sequence].address[i] : 0;
			out[16 + i] = 255;
		}
		bytes = 20;
		event_bytes = 8;
	} else if (step < count + 2) {
		int result = wmt_rom_patch_fragment(&pair[sequence], step - 2, out, capacity);

		if (result < 0)
			return -1;
		bytes = result;
		event_bytes = 5;
	} else {
		if (capacity < 5)
			return -1;
		out[0] = 1;
		out[1] = 7;
		out[2] = 1;
		out[3] = 0;
		out[4] = 4;
		bytes = 5;
		event_bytes = 5;
	}
	expected[0] = 2;
	expected[1] = out[1];
	expected[2] = event_bytes - 4;
	expected[3] = 0;
	for (i = 4; i < event_bytes; i++)
		expected[i] = 0;
	if (event_bytes == 8)
		expected[7] = 1;
	*expected_length = event_bytes;
	return bytes;
}
#endif
