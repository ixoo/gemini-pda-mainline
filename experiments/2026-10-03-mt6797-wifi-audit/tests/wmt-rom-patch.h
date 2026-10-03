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
#endif
