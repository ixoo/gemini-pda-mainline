/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_MTKE_H
#define GEMINI_MTKE_H
#ifdef __KERNEL__
#include <linux/types.h>
#else
#include <stddef.h>
#include <stdint.h>
typedef uint8_t u8;
typedef uint32_t u32;
#endif

#define MTKE_MAX_BYTES (1024U * 1024U)
#define MTKE_MAX_SECTIONS 256U

/*
 * Caller owns immutable data until all views are discarded. No concurrent
 * parse/get or input mutation. Context must not alias input or output views.
 * Context is fixed and small; no section table is stored on the stack.
 */
struct mtke_context {
	const u8 *data;
	size_t size;
	unsigned int count;
	int valid;
};

struct mtke_view {
	const u8 *data;
	u32 offset;
	u32 length;
	u32 destination;
	u32 emi_offset;
	unsigned int emi;
	unsigned int raw_encrypted;
	unsigned int raw_key_index;
	unsigned int encrypted;
	unsigned int key_index;
};

/*
 * Supply standard IEEE CRC32 over the complete supplied span (zlib convention).
 * Kernel adapter below uses crc32_le; no private CRC implementation required.
 */
u32 mtke_crc32(const u8 *data, size_t size);

/*
 * parse: 0 valid, -1 invalid/unsupported structure, -2 unknown reserved
 * semantics (not a corruption claim). Remaining structure may be unchecked.
 * Any failure invalidates prior context.
 */
int mtke_parse(struct mtke_context *ctx, const u8 *data, size_t size);
int mtke_get(const struct mtke_context *ctx, unsigned int index,
	     struct mtke_view *view);
#endif
