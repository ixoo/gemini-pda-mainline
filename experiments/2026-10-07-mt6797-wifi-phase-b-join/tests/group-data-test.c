/* SPDX-License-Identifier: GPL-2.0-only */
/* The protected group-addressed data decoder: exactly the measured class of
 * runtime 17 is named (its logged metadata: 110 bytes, descriptor bytes
 * 08 28 18 04 00 00 04 c0, frame control 0x6208, transmitter the target,
 * receiver not this station); every other byte here (addresses, sequence,
 * body) is a hypothetical fixture value, since the packet's body and receiver
 * address were never recorded. Unicast, unprotected, QoS, fragmented, ordered,
 * power-managed, translated, decrypted, other-status, other-transmitter,
 * non-group-receiver, short and other-type packets are not the class.
 * Exact-size buffers under the sanitizer.
 */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "group-data.h"

static const unsigned char ap[6] = {2, 0, 0, 0, 0, 2};
static const unsigned char other[6] = {2, 0, 0, 0, 0, 9};
static void put16(unsigned char *p, unsigned v) { p[0] = v; p[1] = v >> 8; }

/* Runtime 17's descriptor bytes 4..11 (08 28 18 04 00 00 04 c0), groups as given, then a native
 * header: fc, duration, receiver (group or not), transmitter, addr3, sequence, then 16+body bytes. */
static size_t build(unsigned char *p, unsigned groups, bool pad, unsigned fc, bool group_da, bool ta_ap, size_t body)
{
 size_t off = 16, n;
 memset(p, 0, 512);
 put16(p + 2, 0x4000 | groups << 9);
 p[4] = 0x08; p[5] = 40; p[6] = 24 | (pad ? 0x40 : 0); p[7] = 0x04; p[8] = 0; p[9] = 0; put16(p + 10, 0xc004);
 if (groups & 8) off += 16;
 if (groups & 1) off += 16;
 if (groups & 2) off += 8;
 if (groups & 4) off += 24;
 if (pad) off += 2;
 put16(p + off, fc);
 memset(p + off + 4, group_da ? 0xff : 0x02, 6); if (!group_da) p[off + 9] = 1;
 memcpy(p + off + 10, ta_ap ? ap : other, 6); memcpy(p + off + 16, ap, 6);
 n = off + 24 + 16 + body;
 put16(p, n);
 return n;
}

static bool run(const unsigned char *src, size_t n, struct mt6797_join_group_data *out)
{
 unsigned char *p = malloc(n ? n : 1); assert(p); memcpy(p, src, n);
 memset(out, 0x5a, sizeof(*out));
 bool ok = mt6797_join_group_data(p, n, 40, ap, out);
 free(p); return ok;
}

int main(void)
{
 unsigned char p[512];
 struct mt6797_join_group_data r;
 size_t n = build(p, 0, false, 0x6208, true, true, 54);
 assert(n == 110);
 assert(run(p, n, &r) && r.bytes == 94 && r.fc == 0x6208 && r.match == 0x08 && r.wlan == 0 && r.bss == 1 && r.sec == 0 && r.status == 0xc004);
 /* A declared length below the header plus 16 bytes is refused; from there up
  * to the measured length the class holds with a shorter unexamined body.
  * The wrong channel and another type word are refused. */
 for (size_t cut = 0; cut < n; cut++) { unsigned char q[512]; memcpy(q, p, n); put16(q, cut); assert(run(q, cut, &r) == (cut >= 16 + 24 + 16)); }
 assert(!mt6797_join_group_data(p, n, 36, ap, &r));
 { unsigned char q[512]; memcpy(q, p, n); put16(q + 2, 0xe001); assert(!run(q, n, &r)); put16(q + 2, 0x0000); assert(!run(q, n, &r)); }
 /* Descriptor flags: unicast-to-me refused; neither multicast nor broadcast refused; multicast admitted;
  * translated header, 26-byte header and A-MSDU payload format refused. */
 { unsigned char q[512]; memcpy(q, p, n);
   q[4] = 0x0a; assert(!run(q, n, &r)); q[4] = 0x00; assert(!run(q, n, &r)); q[4] = 0x04; assert(run(q, n, &r) && r.match == 4);
   q[4] = 0x0c; assert(run(q, n, &r) && r.match == 0x0c);
   q[4] = 0x09; assert(!run(q, n, &r));  /* HT control present contradicts the 24-byte header */
   q[4] = 0x18; assert(!run(q, n, &r)); q[4] = 0x28; assert(!run(q, n, &r));  /* beacon bits */
   q[4] = 0x48; assert(!run(q, n, &r)); q[4] = 0x88; assert(!run(q, n, &r));  /* key id bits */
   q[4] = 0x08; q[6] = 0x80 | 14; assert(!run(q, n, &r)); q[6] = 26; assert(!run(q, n, &r)); q[6] = 24; q[7] = 0x05; assert(!run(q, n, &r)); }
 /* Frame control: unprotected, ToDS, QoS data, management, More Fragments,
  * Power Management and Order refused; Retry and More Data free. */
 assert(!run(p, build(p, 0, false, 0x2208, true, true, 54), &r));   /* not protected */
 assert(!run(p, build(p, 0, false, 0x6308, true, true, 54), &r));   /* ToDS as well */
 assert(!run(p, build(p, 0, false, 0x6108, true, true, 54), &r));   /* ToDS instead */
 assert(!run(p, build(p, 0, false, 0x6288, true, true, 54), &r));   /* QoS data */
 assert(!run(p, build(p, 0, false, 0x62d0, true, true, 54), &r));   /* action */
 assert(!run(p, build(p, 0, false, 0x6608, true, true, 54), &r));   /* More Fragments */
 assert(!run(p, build(p, 0, false, 0x7208, true, true, 54), &r));   /* Power Management */
 assert(!run(p, build(p, 0, false, 0xe208, true, true, 54), &r));   /* Order */
 assert(run(p, build(p, 0, false, 0x4208, true, true, 54), &r));    /* no more-data */
 assert(run(p, build(p, 0, false, 0x4a08, true, true, 54), &r));    /* retry */
 /* Descriptor fields bound to the measurement: BSSID field 1, WLAN index 0,
  * security mode 0, status exactly 0xc004 (cipher mismatch, no error flag). */
 n = build(p, 0, false, 0x6208, true, true, 54);
 { unsigned char q[512]; memcpy(q, p, n);
   q[7] = 0x3c; assert(!run(q, n, &r)); q[7] = 0x00; assert(!run(q, n, &r)); q[7] = 0x04;
   q[8] = 1; assert(!run(q, n, &r)); q[8] = 0;
   q[9] = 0x10; assert(!run(q, n, &r)); q[9] = 0x01; assert(!run(q, n, &r)); q[9] = 0x0f; assert(!run(q, n, &r)); q[9] = 0;
   for (unsigned bit = 0; bit < 16; bit++) { put16(q + 10, 0xc004 ^ (1u << bit)); assert(!run(q, n, &r)); }
   put16(q + 10, 0xc004); assert(run(q, n, &r)); }
 /* Addressing: unicast receiver, other transmitter, fragment. */
 assert(!run(p, build(p, 0, false, 0x6208, false, true, 54), &r));
 assert(!run(p, build(p, 0, false, 0x6208, true, false, 54), &r));
 n = build(p, 0, false, 0x6208, true, true, 54); p[16 + 22] = 1; assert(!run(p, n, &r)); p[16 + 22] = 0;
 /* Minimum: the 24-byte header and 16 more bytes; one byte less fails. Nothing about a body is claimed. */
 n = build(p, 0, false, 0x6208, true, true, 0); assert(n == 56 && run(p, n, &r) && r.bytes == 40);
 put16(p, 55); assert(!run(p, 55, &r));
 /* Every group combination and padding. */
 for (unsigned groups = 0; groups < 16; groups++) for (unsigned pad = 0; pad < 2; pad++) {
  n = build(p, groups, pad, 0x6208, true, true, 54);
  assert(run(p, n, &r) && r.bytes == 94);
 }
 mt6797_join_group_data(NULL, 110, 40, ap, &r); mt6797_join_group_data(p, 110, 40, NULL, &r); mt6797_join_group_data(p, 110, 40, ap, NULL);
 puts("group-data: PASS (measured class named; unicast, unprotected, QoS, flags, status, other transmitter, short refused)");
 return 0;
}
