// SPDX-License-Identifier: GPL-2.0-only
#include "mtke.h"

static u32 get32(const u8 *p)
{
	return (u32)p[0] | (u32)p[1] << 8 |
	       (u32)p[2] << 16 | (u32)p[3] << 24;
}

/* Lengths already bounded by the input cap: subtraction avoids end overflow. */
static int overlap(u32 a, u32 n, u32 b, u32 m)
{
	return a <= b ? b - a < n : a - b < m;
}

int mtke_parse(struct mtke_context *ctx, const u8 *data, size_t size)
{
	unsigned int count, i, j;
	size_t table;

	if (!ctx)
		return -1;
	ctx->valid = 0;
	ctx->data = NULL;
	ctx->size = 0;
	ctx->count = 0;
	if (!data || size < 24 || size > MTKE_MAX_BYTES)
		return -1;
	if (data[0] != 'M' || data[1] != 'T' || data[2] != 'K' ||
	    data[3] != 'E')
		return -1;
	count = get32(data + 8);
	if (!count || count > MTKE_MAX_SECTIONS)
		return -1;
	table = 24 + 16 * count;
	if (table > size || mtke_crc32(data + 8, size - 8) != get32(data + 4))
		return -1;
	/* Unknown reserved semantics are unsupported, not evidence of corruption. */
	if (get32(data + 20))
		return -2;
	for (i = 0; i < count; i++) {
		const u8 *p = data + 24 + 16 * i;
		u32 off = get32(p), len = get32(p + 8);
		u32 dst = get32(p + 12), emi = dst & 0xfffffU;

		if (p[6] || p[7])
			return -2;
		if (!len || off < table || off > size ||
		    len > size - off || len - 1 > 0xffffffffU - dst)
			return -1;
		if (i >= 2 && (emi >= 0x80000U || len > 0x80000U - emi))
			return -1;
		for (j = 0; j < i; j++) {
			const u8 *q = data + 24 + 16 * j;
			u32 qlen = get32(q + 8), qdst = get32(q + 12);

			if (overlap(off, len, get32(q), qlen))
				return -1;
			if (i < 2 && overlap(dst, len, qdst, qlen))
				return -1;
			if (i >= 2 && j >= 2 &&
			    overlap(emi, len, qdst & 0xfffffU, qlen))
				return -1;
		}
	}
	ctx->data = data;
	ctx->size = size;
	ctx->count = count;
	ctx->valid = 1;
	return 0;
}

int mtke_get(const struct mtke_context *ctx, unsigned int index,
	     struct mtke_view *view)
{
	const u8 *p;

	if (!view)
		return -1;
	*view = (struct mtke_view){ 0 };
	if (!ctx || !ctx->valid || index >= ctx->count)
		return -1;
	p = ctx->data + 24 + 16 * index;
	view->offset = get32(p);
	view->data = ctx->data + view->offset;
	view->length = get32(p + 8);
	view->destination = get32(p + 12);
	view->emi = index >= 2;
	view->emi_offset = view->emi ? view->destination & 0xfffffU : 0;
	view->raw_encrypted = p[5];
	view->raw_key_index = p[4];
	view->encrypted = !view->emi && p[5] != 0;
	view->key_index = view->encrypted ? p[4] & 3U : 0;
	return 0;
}
