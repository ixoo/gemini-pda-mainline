/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "eapol-rx.h"

static const unsigned char own[6] = {2, 0, 0, 0, 0, 1};
static const unsigned char ap[6] = {2, 0, 0, 0, 0, 2};
static const unsigned char origin[6] = {2, 0, 0, 0, 0, 3};
static unsigned char expected[32] = {
 8, 2, 0, 0, 2, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 2,
 2, 0, 0, 0, 0, 3, 0x30, 0x12, 0xaa, 0xaa, 3, 0, 0, 0, 0x88, 0x8e
};
static size_t payload_at, vector_at;
static void put16(unsigned char *p, unsigned value)
{ p[0] = value; p[1] = value >> 8; }
static size_t fixture(unsigned char *p, unsigned groups, bool translated,
                      bool padding, unsigned data_bytes)
{
 size_t off = 16;
 memset(p, 0, 4096);
 put16(p + 2, 0x4000 | groups << 9);
 p[4] = 2; p[5] = 40; p[6] = translated ? 0x8e : 24;
 if (padding) p[6] |= 0x40;
 p[8] = 1; put16(p + 10, 0xc000);
 if (groups & 8) {
  p[off] = 8; p[off + 1] = 2;
  memcpy(p + off + 2, ap, 6); put16(p + off + 8, 0x1230); off += 16;
 }
 if (groups & 1) off += 16;
 if (groups & 2) off += 8;
 vector_at = 0;
 if (groups & 4) { vector_at = off; p[off + 9] = 51; off += 24; }
 if (padding) off += 2;
 if (translated) {
  memcpy(p + off, own, 6); memcpy(p + off + 6, origin, 6);
  p[off + 12] = 0x88; p[off + 13] = 0x8e; payload_at = off + 14;
 } else {
  memcpy(p + off, expected, 32); payload_at = off + 32;
 }
 p[payload_at] = 2; p[payload_at + 1] = 3;
 unsigned length = 95 + data_bytes;
 p[payload_at + 2] = length >> 8; p[payload_at + 3] = length;
 p[payload_at + 4] = 2; /* RSN descriptor */
 p[payload_at + 5] = 0; p[payload_at + 6] = 0x8a; /* M1-style key info */
 p[payload_at + 8] = 16;
 p[payload_at + 97] = data_bytes >> 8; p[payload_at + 98] = data_bytes;
 for (unsigned i = 0; i < data_bytes; i++) p[payload_at + 99 + i] = i;
 size_t bytes = payload_at + length + 4; put16(p, bytes); return bytes;
}
static void reject(const unsigned char *p, size_t n)
{
 struct mt6797_eapol_rx out, before;
 memset(&out, 0xa5, sizeof(out)); memcpy(&before, &out, sizeof(out));
 assert(!mt6797_eapol_rx(p, n, 40, own, ap, &out));
 assert(!memcmp(&out, &before, sizeof(out)));
}
static void mutation(unsigned char *p, size_t n, size_t off, unsigned char bits)
{ p[off] ^= bits; reject(p, n); p[off] ^= bits; }
int main(void)
{
 unsigned char *p = malloc(4096); assert(p);
 unsigned cases = 0;
 for (unsigned groups = 0; groups < 16; groups++) {
  for (unsigned trans = 0; trans < 2; trans++) {
   if (trans && !(groups & 8)) continue;
   for (unsigned pad = 0; pad < 2; pad++) {
    size_t n = fixture(p, groups, trans, pad, 22);
    struct mt6797_eapol_rx out;
    assert(mt6797_eapol_rx(p, n, 40, own, ap, &out));
    assert(out.signal_valid == !!(groups & 4));
    assert(out.signal_dbm == (vector_at ? -85 : 0));
    assert(out.offset <= n && out.bytes == n - out.offset);
    assert(out.prefix_bytes == (trans ? 32 : 0));
    if (trans) {
     assert(!memcmp(out.prefix, expected, 32));
     assert(out.offset == payload_at && out.bytes == 121);
    } else {
     assert(!memcmp(p + out.offset, expected, 32));
     assert(out.bytes == 153);
    }
    for (size_t cut = 0; cut < n; cut++) {
     unsigned char *short_packet = malloc(cut ? cut : 1); assert(short_packet);
     memcpy(short_packet, p, cut);
     if (cut >= 2) put16(short_packet, cut);
     reject(short_packet, cut); free(short_packet);
    }
    mutation(p, n, 0, 1); /* RX byte count */
    mutation(p, n, 3, 0x20); /* packet type */
    mutation(p, n, 4, 1); /* HTC */
    mutation(p, n, 5, 1); /* channel */
    mutation(p, n, 6, 1); /* header length */
    mutation(p, n, 7, 4); /* BSS index 1: not admitted */
    mutation(p, n, 7, 0x40); /* BSS index 16: not admitted */
    mutation(p, n, 7, 1); /* payload format: not an MSDU */
    mutation(p, n, 7, 0x3d); /* no-match BSS with A-MSDU payload format */
    p[7] = 0x3c; /* runtime 11 measured BSS field 15, payload format 0 */
    assert(mt6797_eapol_rx(p, n, 40, own, ap, &out) && out.bss_index == 15);
    p[7] = 0;
    assert(mt6797_eapol_rx(p, n, 40, own, ap, &out) && out.bss_index == 0);
    mutation(p, n, 8, 1); /* WLAN owner */
    mutation(p, n, 9, 0x40); /* firmware CCMP, not clear */
    for (unsigned bit = 0; bit < 16; bit++) mutation(p, n, 10 + bit / 8, 1 << (bit % 8));
    if (vector_at) {
     unsigned char rcpi = p[vector_at + 9]; p[vector_at + 9] = 221;
     reject(p, n); p[vector_at + 9] = rcpi;
    }
    mutation(p, n, payload_at, 4); /* invalid EAPOL version */
    mutation(p, n, payload_at + 1, 1); /* not EAPOL-Key */
    mutation(p, n, payload_at + 2, 1); /* declared body */
    mutation(p, n, payload_at + 4, 1); /* not RSN descriptor */
    mutation(p, n, payload_at + 98, 1); /* declared key data */
    size_t fc = trans ? 16 : payload_at - 32;
    size_t sequence = trans ? 24 : payload_at - 10;
    size_t destination = trans ? payload_at - 14 : payload_at - 28;
    size_t transmitter = trans ? 18 : payload_at - 22;
    size_t source = trans ? payload_at - 8 : payload_at - 16;
    mutation(p, n, destination, 2); mutation(p, n, transmitter, 2);
    mutation(p, n, source, 1); mutation(p, n, sequence, 1);
    mutation(p, n, fc, 0x80); mutation(p, n, fc + 1, 0x40);
    mutation(p, n, fc + 1, 1); /* wrong DS direction */
    for (unsigned version = 1; version <= 3; version++) {
     p[payload_at] = version;
     assert(mt6797_eapol_rx(p, n, 40, own, ap, &out));
    }
    p[fc + 1] |= 0x28;
    assert(mt6797_eapol_rx(p, n, 40, own, ap, &out));
    cases++;
   }
  }
 }
 size_t n = fixture(p, 12, true, false, 0);
 assert(mt6797_eapol_rx(p, n, 40, own, ap, &(struct mt6797_eapol_rx){0}));
 p[3] &= ~0x10; reject(p, n); /* translated without group 4 */
 /* Runtime 10 measured a refused 147-byte data packet with group 4 only:
  * a translated frame with the header padding bit and a 95-byte EAPOL-Key
  * body has exactly that length. The fields built here are a hypothetical
  * source-valid case of that arithmetic, not fields of the captured packet,
  * which was never captured; the length match is consistency, not identity.
  */
 n = fixture(p, 8, true, true, 0);
 assert(n == 147);
 struct mt6797_eapol_rx no_vector;
 assert(mt6797_eapol_rx(p, n, 40, own, ap, &no_vector));
 assert(!no_vector.signal_valid && no_vector.signal_dbm == 0 && no_vector.bytes == 99 && no_vector.prefix_bytes == 32);
 /* The runtime-11 base header, byte for byte (match 0x02, channel 40, 0xce,
  * 0x3c, WLAN 1, 0x00, status 0xc000), on that hypothetical body: admitted
  * with BSS field 15 and no signal. Still a hypothetical body.
  */
 memcpy(p + 4, (const unsigned char[]){0x02, 0x28, 0xce, 0x3c, 0x01, 0x00, 0x00, 0xc0}, 8);
 assert(mt6797_eapol_rx(p, n, 40, own, ap, &no_vector) && no_vector.bss_index == 15 && !no_vector.signal_valid);
 n = fixture(p, 12, true, false, 0);
 p[3] &= ~8; reject(p, n); /* group 3 flagged absent while its bytes remain: layout mismatch */
 n = fixture(p, 12, true, false, 1953); /* maximum body 2048 */
 assert(mt6797_eapol_rx(p, n, 40, own, ap, &(struct mt6797_eapol_rx){0}));
 n = fixture(p, 12, true, false, 1954); reject(p, n);
 assert(!mt6797_eapol_rx(NULL, 0, 40, own, ap, NULL));
 free(p); printf("eapol-decoder: %u layout/padding cases, all truncations and malformed metadata passed\n", cases);
 return 0;
}
