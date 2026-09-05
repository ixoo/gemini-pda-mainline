/* SPDX-License-Identifier: GPL-2.0-only */
/* Standalone host-only sanitizer harness; all bytes are synthetic. */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include "mtke.h"

u32 mtke_crc32(const u8 *data, size_t size)
{
	return (u32)crc32(0, data, (uInt)size);
}

static void put32(u8 *p, u32 value)
{
	unsigned int i;

	for (i = 0; i < 4; i++)
		p[i] = (u8)(value >> (8 * i));
}

static void seal(u8 *p, size_t size)
{
	put32(p + 4, mtke_crc32(p + 8, size - 8));
}

static void fixture(u8 *p, unsigned int count)
{
	unsigned int i;
	size_t size = 24 + 24 * count;

	memset(p, 0, size);
	memcpy(p, "MTKE", 4);
	put32(p + 8, count);
	for (i = 0; i < count; i++) {
		u8 *entry = p + 24 + 16 * i;

		put32(entry, 24 + 16 * count + 8 * i);
		entry[4] = 255;
		entry[5] = 128;
		put32(entry + 8, 8);
		put32(entry + 12, 8 * i);
	}
	seal(p, size);
}

static unsigned int cases;

/* Exact allocation: no ctypes trailing NUL or spare readable capacity. */
static void check(const u8 *source, size_t size, int expected)
{
	struct mtke_context ctx = {0};
	struct mtke_view view;
	u8 *p = size ? malloc(size) : NULL;
	int result;
	unsigned int i;

	assert(!size || p);
	if (size)
		memcpy(p, source, size);
	result = mtke_parse(&ctx, p, size);
	if (expected != 99)
		assert(result == expected);
	if (!result) {
		for (i = 0; i < ctx.count; i++) {
			assert(!mtke_get(&ctx, i, &view));
			assert(view.data == p + view.offset);
			assert(view.length <= size - view.offset);
			/* Touch both ends of every accepted payload under ASan. */
			assert(view.data[0] == source[view.offset]);
			assert(view.data[view.length - 1] ==
			       source[view.offset + view.length - 1]);
		}
		assert(mtke_get(&ctx, ctx.count, &view) == -1);
		/* Failure must revoke an already successful context. */
		assert(mtke_parse(&ctx, NULL, 0) == -1);
	}
	assert(!ctx.valid && !ctx.count && !ctx.data && !ctx.size);
	memset(&view, 0xa5, sizeof(view));
	assert(mtke_get(&ctx, 0, &view) == -1);
	assert(!view.data && !view.length && !view.offset && !view.destination);
	assert(!view.emi && !view.emi_offset && !view.raw_encrypted);
	assert(!view.raw_key_index && !view.encrypted && !view.key_index);
	assert(mtke_get(&ctx, UINT_MAX, &view) == -1);
	free(p);
	cases++;
}

int main(void)
{
	u8 base[120], changed[120];
	u8 *large = malloc(MTKE_MAX_BYTES + 1);
	const u32 edges[] = {
		0, 1, 23, 24, 87, 88, 119, 120, 121, 256, 257,
		0x7ffff, 0x80000, 0xfffff, 0xfffffff8, 0xfffffff9, 0xffffffff
	};
	unsigned int i, j;

	assert(large);
	fixture(base, 4);
	check(base, sizeof(base), 0);
	for (i = 0; i < sizeof(base); i++)
		check(base, i, -1);
	for (i = 8; i < 88; i += 4) {
		for (j = 0; j < sizeof(edges) / sizeof(edges[0]); j++) {
			memcpy(changed, base, sizeof(base));
			put32(changed + i, edges[j]);
			seal(changed, sizeof(changed));
			check(changed, sizeof(changed), 99);
		}
	}
	memcpy(changed, base, sizeof(base));
	put32(changed + 36, 0xfffffff8);
	seal(changed, sizeof(changed));
	check(changed, sizeof(changed), 0);
	put32(changed + 36, 0xfffffff9);
	seal(changed, sizeof(changed));
	check(changed, sizeof(changed), -1);
	/* Reserved refusal can precede an invalid later entry. */
	put32(changed + 20, 1);
	seal(changed, sizeof(changed));
	check(changed, sizeof(changed), -2);
	memset(large, 0, MTKE_MAX_BYTES + 1);
	fixture(large, 256);
	check(large, 24 + 24 * 256, 0);
	for (i = 24; i < 24 + 16 * 256; i++)
		check(large, i, -1);
	seal(large, MTKE_MAX_BYTES);
	check(large, MTKE_MAX_BYTES, 0);
	check(large, MTKE_MAX_BYTES + 1, -1);
	assert(mtke_parse(NULL, NULL, 0) == -1);
	assert(mtke_get(NULL, 0, NULL) == -1);
	free(large);
	printf("PASS: %u exact-allocation sanitizer cases\n", cases);
	return 0;
}
