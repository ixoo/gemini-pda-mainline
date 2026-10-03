/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wmt-rom-patch.h"
#include "wmt-full-stp-state.h"

static void selected_sequence(void)
{
	static unsigned char bodies[2][210876];
	struct wmt_rom_patch pair[2] = {
		{ bodies[0], 46444, 1, { 0, 0, 10, 240 } },
		{ bodies[1], 210876, 2, { 0, 0, 9, 0 } }
	};
	struct wmt_full_state link;
	unsigned char command[1005], frame[1011], event[8], saved[1005], saved_event[8];
	unsigned int ordinal, i, event_bytes, saved_length, addresses = 0, fragments = 0, resets = 0;
	int bytes, encoded;

	wmt_full_state_init(&link);
	for (ordinal = 0; ordinal < 264; ordinal++) {
		bytes = mt6797_wmt_rom_step(pair, ordinal, command, sizeof(command), event, &event_bytes);
		assert(bytes > 0 && (unsigned int)(command[2] | command[3] << 8) == (unsigned int)bytes - 4);
		if (ordinal == 0 || ordinal == 1 || ordinal == 50 || ordinal == 51) {
			unsigned int register_address = command[8] | command[9] << 8 |
				command[10] << 16 | command[11] << 24;

			addresses++;
			assert(bytes == 20 && event_bytes == 8 && event[7] == 1);
			assert(register_address == ((ordinal == 0 || ordinal == 50) ? 0x02090508U : 0x02090b2cU));
			for (i = 16; i < 20; i++)
				assert(command[i] == 255);
			assert(command[12] == 0);
			if (ordinal == 1)
				assert(!memcmp(command + 12, pair[0].address, 4));
			if (ordinal == 51)
				assert(!memcmp(command + 12, pair[1].address, 4));
		} else if (ordinal == 49 || ordinal == 263) {
			resets++;
			assert(bytes == 5 && command[1] == 7 && command[4] == 4);
			assert(event_bytes == 5 && event[1] == 7 && !event[4]);
		} else {
			fragments++;
			assert(command[1] == 1 && event_bytes == 5 && event[1] == 1 && !event[4]);
			assert(command[4] == ((ordinal == 2 || ordinal == 52) ? 1 :
				(ordinal == 48 || ordinal == 262) ? 3 : 2));
		}
		/* Host epoch continues across both ordinary WMT resets. */
		assert(link.tx_next == (ordinal & 7) && link.rx_next == (ordinal & 7));
		encoded = wmt_full_encode(frame, sizeof(frame), command, bytes, link.tx_next, link.local_ack);
		assert(encoded == bytes + 6 && wmt_full_sent(&link, link.tx_next) == 0);
		encoded = wmt_full_encode(frame, sizeof(frame), event, event_bytes, link.rx_next, ordinal & 7);
		assert(wmt_full_receive(&link, frame, encoded, event, event_bytes) == 1);
		assert(wmt_full_ack_sent(&link, link.local_ack) == 0);
		assert(wmt_full_finish(&link) == 0);
	}
	assert(addresses == 4 && fragments == 258 && resets == 2 && !link.active);
	memset(command, 0xa5, sizeof(command));
	memset(event, 0x5a, sizeof(event));
	memcpy(saved, command, sizeof(command));
	memcpy(saved_event, event, sizeof(event));
	event_bytes = saved_length = 99;
	assert(mt6797_wmt_rom_step(pair, 264, command, sizeof(command), event, &event_bytes) == -1);
	assert(mt6797_wmt_rom_step(pair, 0, command, 19, event, &event_bytes) == -1);
	assert(mt6797_wmt_rom_step(pair, 2, command, 1004, event, &event_bytes) == -1);
	assert(mt6797_wmt_rom_step(pair, 49, command, 4, event, &event_bytes) == -1);
	pair[0].sequence = 2;
	assert(mt6797_wmt_rom_step(pair, 0, command, sizeof(command), event, &event_bytes) == -1);
	pair[0].sequence = 1;
	pair[1].address[3] = 1;
	assert(mt6797_wmt_rom_step(pair, 50, command, sizeof(command), event, &event_bytes) == -1);
	pair[1].address[3] = 0;
	pair[1].length--;
	assert(mt6797_wmt_rom_step(pair, 50, command, sizeof(command), event, &event_bytes) == -1);
	assert(!memcmp(command, saved, sizeof(command)) && !memcmp(event, saved_event, sizeof(event)));
	assert(event_bytes == saved_length);
}

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
	selected_sequence();
	puts("rom_patch_sequence=pass; rom_patch_constructor=pass; synthetic_inputs_only; hardware_actions=none");
	return 0;
}
