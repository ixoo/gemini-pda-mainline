/* SPDX-License-Identifier: GPL-2.0-only */
/* H:4 reassembly across arbitrary STP payload boundaries. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "btmt6797-h4.h"

struct out {
	unsigned int count, types[8], lengths[8];
};

static int emit(void *context, unsigned char type, const unsigned char *p, unsigned int n)
{
	struct out *o = context;

	(void)p;
	o->types[o->count] = type;
	o->lengths[o->count++] = n;
	return 0;
}

int main(void)
{
	unsigned char stream[2200];
	unsigned int used = 0, cut, i;
	struct bt_h4 h;
	struct out o;

	/* Event, ACL with 1021-byte body, zero-length event, SCO. */
	stream[used++] = 0x04; stream[used++] = 0x0e; stream[used++] = 4;
	memcpy(stream + used, "\x01\x03\x0c\x00", 4); used += 4;
	stream[used++] = 0x02; stream[used++] = 0x01; stream[used++] = 0x20;
	stream[used++] = 1021 & 255; stream[used++] = 1021 >> 8;
	memset(stream + used, 0x5a, 1021); used += 1021;
	stream[used++] = 0x04; stream[used++] = 0xff; stream[used++] = 0;
	stream[used++] = 0x03; stream[used++] = 0x01; stream[used++] = 0x00; stream[used++] = 3;
	memcpy(stream + used, "abc", 3); used += 3;
	/* Every split point and odd chunk sizes yield the same four packets. */
	for (cut = 1; cut < 40; cut++) {
		bt_h4_reset(&h);
		memset(&o, 0, sizeof(o));
		for (i = 0; i < used; i += cut)
			assert(bt_h4_feed(&h, stream + i, used - i < cut ? used - i : cut,
					  emit, &o) == 0);
		assert(o.count == 4 && o.types[0] == 4 && o.lengths[0] == 6);
		assert(o.types[1] == 2 && o.lengths[1] == 1025);
		assert(o.types[2] == 4 && o.lengths[2] == 2);
		assert(o.types[3] == 3 && o.lengths[3] == 6);
		assert(h.used == 0);
	}
	/* Bad type and oversize ACL are terminal. */
	bt_h4_reset(&h);
	memset(&o, 0, sizeof(o));
	assert(bt_h4_feed(&h, (const unsigned char *)"\x05", 1, emit, &o) == -1);
	assert(bt_h4_feed(&h, (const unsigned char *)"\x04", 1, emit, &o) == -1);
	bt_h4_reset(&h);
	assert(bt_h4_feed(&h, (const unsigned char *)"\x02\x01\x20\xff\x0f", 5, emit, &o) == -1);
	assert(o.count == 0);
	puts("bt h4: reassembly at every split, bounds and bad types pass");
	return 0;
}
