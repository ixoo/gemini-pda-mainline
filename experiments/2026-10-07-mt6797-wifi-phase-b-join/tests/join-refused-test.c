/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "join-refused.h"

static const unsigned char own[6] = {2, 0, 0, 0, 0, 1};
static const unsigned char ap[6] = {2, 0, 0, 0, 0, 2};
static const unsigned char other[6] = {2, 0, 0, 0, 0, 9};
#define U MT6797_JOIN_REFUSED_UNKNOWN

static void put16(unsigned char *p, unsigned v) { p[0] = v; p[1] = v >> 8; }

/* Exact-size buffers so the sanitizer proves nothing past the packet is read. */
static struct mt6797_join_refused run(const unsigned char *src, size_t n, const unsigned char *target)
{
 unsigned char *p = malloc(n ? n : 1); assert(p); memcpy(p, src, n);
 struct mt6797_join_refused r; memset(&r, 0x5a, sizeof(r));
 mt6797_join_refused_summary(p, n, own, target, &r);
 free(p); return r;
}

static void uninterpreted(struct mt6797_join_refused r, unsigned type)
{
 static const unsigned char zero[8];
 assert(r.type == type && !r.base_valid && !memcmp(r.hdr, zero, 8) && !r.groups && !r.at);
 assert(r.g4fc == U && r.g4seq == U && !r.g4ta && !r.translated && r.first == U);
 assert(!r.sec && !r.to_own && !r.from_ap);
}

/* A data-type RXD: base 16, optional group 4 (fc, TA, seq), optional pad,
 * then a wire header and payload as `body` says.
 */
static size_t data_packet(unsigned char *p, bool group4, bool pad, unsigned hdrlen_field, bool translated,
                          const unsigned char *body, size_t body_bytes, bool ta_is_ap)
{
 size_t off = 16;
 memset(p, 0, 512);
 put16(p + 2, 0x4000 | (group4 ? 8 : 0) << 9 | 0x1af);
 p[4] = 2; p[5] = 40; p[6] = (translated ? 0x80 : 0) | (pad ? 0x40 : 0) | (hdrlen_field & 0x3f);
 p[8] = 1; put16(p + 10, 0xc000);
 if (group4) {
  put16(p + off, 0x0208); memcpy(p + off + 2, ta_is_ap ? ap : other, 6); put16(p + off + 8, 0x1230); off += 16;
 }
 if (pad) off += 2;
 memcpy(p + off, body, body_bytes); off += body_bytes;
 put16(p, off); return off;
}

int main(void)
{
 unsigned char p[512], eth[113], native[120];
 struct mt6797_join_refused r;
 size_t n;

 /* 1. Below four bytes: only sentinels. */
 memset(p, 0xff, sizeof(p));
 for (n = 0; n < 4; n++) uninterpreted(run(p, n, ap), U);
 /* 2. Packet types without the descriptor layout (event 7, TX status 0), a
  *    declared length that differs from the buffer, and a short base: the
  *    type word is reported, nothing else is interpreted. A software frame
  *    (the vendor SW_FRAME type word) has the layout and is interpreted.
  */
 memset(eth, 0xee, sizeof(eth));
 n = data_packet(p, true, true, 14, true, eth, sizeof(eth), true);
 assert(n == 147);
 put16(p + 2, 0xe001 | 8 << 9); r = run(p, n, ap);
 assert(r.type == 0xf001 && r.base_valid && r.groups == 8 && r.at == 34 && r.translated && r.first == 0xeeee);
 put16(p + 2, 0xe000); uninterpreted(run(p, n, ap), 0xe000);
 put16(p + 2, 0x0000); uninterpreted(run(p, n, ap), 0x0000);
 put16(p + 2, 0x4000 | 8 << 9 | 0x1af);
 put16(p, n - 1); uninterpreted(run(p, n, ap), 0x51af);
 put16(p, n);
 uninterpreted(run(p, 15, ap), 0x51af); /* declared 147, only 15 present */
 /* 3. A hypothetical source-valid packet with runtime 10's measured length
  *    and type word (data type, group 4 only, padding, translated with header
  *    length 14, 147 bytes); its fields are the fixture's, not the captured
  *    packet's. Interpreted fields appear; the Ethernet type is the only
  *    payload-adjacent word, and it is the type field, not data.
  */
 memset(eth, 0xee, sizeof(eth)); eth[12] = 0x88; eth[13] = 0x8e;
 n = data_packet(p, true, true, 14, true, eth, sizeof(eth), true);
 r = run(p, n, ap);
 assert(r.type == 0x51af && r.base_valid && r.groups == 8 && r.at == 34 && r.translated);
 assert(r.hdr[0] == 2 && r.hdr[1] == 40 && r.hdr[2] == 0xce && r.hdr[4] == 1 && r.hdr[6] == 0 && r.hdr[7] == 0xc0);
 assert(r.g4fc == 0x0208 && r.g4seq == 0x1230 && r.g4ta && r.first == 0x888e);
 assert(!r.sec && !r.to_own && !r.from_ap); /* Ethernet DA is 0xee.., not this station */
 r = run(p, n, other); assert(!r.g4ta && r.first == 0x888e);
 r = run(p, n, NULL); assert(!r.g4ta);
 memcpy(eth, own, 6); n = data_packet(p, true, true, 14, true, eth, sizeof(eth), true);
 r = run(p, n, ap); assert(r.to_own && !r.from_ap && r.first == 0x888e);
 p[9] = 0x10; r = run(p, n, ap); assert(r.sec == 1 && r.to_own); p[9] = 0;
 memset(eth, 0xee, sizeof(eth));
 /* 4. Translated with a header length other than 14, or fewer than 14 bytes
  *    after the groups: the first word is unknown; group-4 fields stay.
  */
 n = data_packet(p, true, true, 24, true, eth, sizeof(eth), true);
 r = run(p, n, ap); assert(r.base_valid && r.first == U && r.g4fc == 0x0208);
 n = data_packet(p, true, true, 14, true, eth, 13, true);
 r = run(p, n, ap); assert(r.base_valid && r.first == U && r.at == 34);
 /* 5. Native: a 24-byte header yields its frame control; a QoS header (26)
  *    too; a header length larger than the remaining bytes does not; a
  *    header length below 24 does not.
  */
 memset(native, 0xee, sizeof(native)); put16(native, 0x0008);
 n = data_packet(p, false, false, 24, false, native, sizeof(native), true);
 r = run(p, n, ap); assert(r.base_valid && !r.groups && r.at == 16 && r.first == 0x0008 && r.g4fc == U && !r.g4ta);
 assert(!r.to_own && !r.from_ap);
 memcpy(native + 4, own, 6); memcpy(native + 10, ap, 6);
 n = data_packet(p, false, false, 24, false, native, sizeof(native), true);
 r = run(p, n, ap); assert(r.to_own && r.from_ap);
 r = run(p, n, other); assert(r.to_own && !r.from_ap);
 /* A software frame with the native management header (runtime 16's refused
  * packet shape: groups 1 to 3, 72 wire bytes): interpreted, frame control
  * reported, receiver and transmitter flags from the whole header.
  */
 memset(p, 0, sizeof(p)); put16(p + 2, 0xe001 | 7 << 9); p[4] = 2; p[5] = 40; p[6] = 24; p[8] = 1; put16(p + 10, 0xc000);
 put16(p + 64, 0x00d0); memcpy(p + 68, own, 6); memcpy(p + 74, ap, 6); memcpy(p + 80, ap, 6);
 put16(p, 136); r = run(p, 136, ap);
 assert(r.type == 0xee01 && r.base_valid && r.groups == 7 && r.at == 64 && !r.translated && r.first == 0x00d0);
 assert(r.g4fc == U && !r.g4ta && !r.sec && r.to_own && r.from_ap);
 memset(native, 0xee, sizeof(native)); put16(native, 0x0008);
 put16(native, 0x0088);
 n = data_packet(p, true, false, 26, false, native, 26, true);
 r = run(p, n, ap); assert(r.first == 0x0088 && r.at == 32 && r.g4fc == 0x0208);
 n = data_packet(p, true, false, 26, false, native, 25, true);
 r = run(p, n, ap); assert(r.first == U);
 n = data_packet(p, false, false, 23, false, native, sizeof(native), true);
 r = run(p, n, ap); assert(r.first == U);
 /* 6. Group 4 flagged but the packet ends inside it: no group-4 fields, no
  *    first word; the header offset is still the declared arithmetic.
  */
 n = data_packet(p, true, false, 14, true, eth, 0, true);
 put16(p, 20); r = run(p, 20, ap);
 assert(r.base_valid && r.groups == 8 && r.at == 32 && r.g4fc == U && r.g4seq == U && !r.g4ta && r.first == U);
 /* 7. Every group combination: the offset follows the source-defined sizes
  *    and the first word is unknown whenever the header is not whole.
  */
 for (unsigned groups = 0; groups < 16; groups++) {
  memset(p, 0, sizeof(p)); put16(p + 2, 0x4000 | groups << 9); p[6] = 24;
  put16(p, 40); r = run(p, 40, ap);
  size_t at = 16 + ((groups & 8) ? 16 : 0) + ((groups & 1) ? 16 : 0) + ((groups & 2) ? 8 : 0) + ((groups & 4) ? 24 : 0);
  assert(r.base_valid && r.groups == groups && r.at == at);
  assert(r.first == (at + 24 <= 40 ? 0 : U));
  assert((r.g4fc != U) == ((groups & 8) != 0));
 }
 assert((mt6797_join_refused_summary(NULL, 147, own, ap, &r), r.type == U && !r.base_valid));
 mt6797_join_refused_summary(p, 40, own, ap, NULL);
 puts("join-refused: PASS (bounded summary; unknown kinds uninterpreted; exact buffers under ASan)");
 return 0;
}
