/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wmt-rom-patch.h"
#include "wmt-full-stp.h"

int main(void)
{
	static const unsigned int lengths[] = { 46444, 210876 };
	static const unsigned char addresses[][3] = { { 0, 10, 240 }, { 0, 9, 0 } };
	unsigned char command[1005], frame[1011], before[1005], tiny[] = { 17 };
	struct wmt_rom_patch patch, saved;
	struct wmt_full_frame decoded;
	unsigned char *file;
	unsigned int sequence, i, index, count, total;
	int bytes, framed;

	for (sequence = 1; sequence <= 2; sequence++) {
		file = calloc(lengths[sequence - 1] + 28, 1);
		assert(file);
		file[24] = 0x20 | sequence;
		memcpy(file + 25, addresses[sequence - 1], 3);
		for (i = 0; i < lengths[sequence - 1]; i++)
			file[28 + i] = i;
		assert(wmt_rom_patch_parse(file, lengths[sequence - 1] + 28, sequence, &patch) == 0);
		assert(patch.body == file + 28 && patch.sequence == sequence && patch.address[0] == 0);
		count = (patch.length + 999) / 1000;
		assert(count == (sequence == 1 ? 47 : 211));
		total = 0;
		for (index = 0; index < count; index++) {
			bytes = wmt_rom_patch_fragment(&patch, index, command, sizeof(command));
			assert(bytes == (index == count - 1 ? (sequence == 1 ? 449 : 881) : 1005));
			assert(command[0] == 1 && command[1] == 1);
			assert((unsigned int)(command[2] | (command[3] << 8)) == (unsigned int)bytes - 4);
			assert(command[4] == (index == count - 1 ? 3 : index == 0 ? 1 : 2));
			assert(!memcmp(command + 5, patch.body + total, bytes - 5));
			total += bytes - 5;
			framed = wmt_full_encode(frame, sizeof(frame), command, bytes, index & 7, 7);
			assert(wmt_full_decode(frame, framed, &decoded) == 1);
			assert(!memcmp(decoded.payload, command, bytes));
		}
		assert(total == patch.length);
		memcpy(&saved, &patch, sizeof(patch));
		assert(wmt_rom_patch_parse(file, 28, sequence, &patch) == -1);
		assert(wmt_rom_patch_parse(file, lengths[sequence - 1] + 27, sequence, &patch) == -1);
		assert(wmt_rom_patch_parse(file, lengths[sequence - 1] + 28, 3 - sequence, &patch) == -1);
		file[24] ^= 0x10;
		assert(wmt_rom_patch_parse(file, lengths[sequence - 1] + 28, sequence, &patch) == -1);
		file[24] ^= 0x10;
		file[27] ^= 1;
		assert(wmt_rom_patch_parse(file, lengths[sequence - 1] + 28, sequence, &patch) == -1);
		assert(!memcmp(&patch, &saved, sizeof(patch)));
		memset(command, 0xa5, sizeof(command));
		memcpy(before, command, sizeof(command));
		assert(wmt_rom_patch_fragment(&patch, count, command, sizeof(command)) == -1);
		assert(wmt_rom_patch_fragment(&patch, 0, command, 1004) == -1);
		assert(wmt_rom_patch_fragment(&patch, ~0U, command, sizeof(command)) == -1);
		assert(!memcmp(command, before, sizeof(command)));
		free(file);
	}
	/* Source last-fragment rule includes a one-fragment synthetic body. */
	patch.body = tiny;
	patch.length = 1;
	assert(wmt_rom_patch_fragment(&patch, 0, command, sizeof(command)) == 6);
	assert(command[2] == 2 && command[3] == 0 && command[4] == 3 && command[5] == 17);
	puts("rom_patch_constructor=pass; synthetic_inputs_only; hardware_actions=none");
	return 0;
}
