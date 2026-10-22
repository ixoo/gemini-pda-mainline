/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stddef.h>
#include "snapshot-sets.h"
int main(void)
{
	struct mt6797_snapshot_range r[] = {{0x100, 3}, {0x400, 2}};
	struct mt6797_snapshot_set s = {"synthetic", r, 2};
	const unsigned int expected[] = {0x100, 0x104, 0x108, 0x400, 0x404};
	unsigned int address = 0xfeed, i;
	assert(mt6797_snapshot_set_words(&s) == 5);
	for (i = 0; i < 5; i++) {
		assert(mt6797_snapshot_set_address(&s, i, &address));
		assert(address == expected[i]);
	}
	address = 0xfeed;
	assert(!mt6797_snapshot_set_address(&s, 5, &address) && address == 0xfeed);
	r[0].first = 0x102;
	assert(!mt6797_snapshot_set_words(&s));
	r[0].first = 0;
	r[0].words = 2047; r[1].words = 1;
	assert(mt6797_snapshot_set_words(&s) == 2048);
	r[0].words++;
	assert(!mt6797_snapshot_set_words(&s));
	r[0].first = 0xfffffffcU; r[0].words = 2;
	assert(!mt6797_snapshot_set_words(&s));
	r[0].words = 1;
	assert(mt6797_snapshot_set_words(&s) == 2);
	r[0].words = 0;
	assert(!mt6797_snapshot_set_words(&s));
	assert(!mt6797_snapshot_set_words(NULL));
	assert(!mt6797_snapshot_set_address(NULL, 0, &address));
	return 0;
}
