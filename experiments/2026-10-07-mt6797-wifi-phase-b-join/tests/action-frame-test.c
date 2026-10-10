/* SPDX-License-Identifier: GPL-2.0-only */
/* The directed clear Action frame decoder: exactly the measured class of
 * runtime 18 is named (logged metadata: 136 bytes, type word 0xee01 with
 * groups 1 to 3, descriptor bytes 02 28 18 04 01 00 00 e0, frame control
 * 0x00d0, receiver this station, transmitter the target); the receiver and
 * transmitter addresses here are fixture values consistent with the logged
 * flags, and the sequence and body (including the category byte) are
 * hypothetical and never read. Protected, Action No Ack, other subtypes,
 * group-addressed, other peer, other descriptor bytes, other status, other
 * group sets, padding, short and other-type packets are not the class.
 * Exact-size buffers under the sanitizer.
 */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "action-frame.h"

static const unsigned char own[6] = {2, 0, 0, 0, 0, 1};
static const unsigned char ap[6] = {2, 0, 0, 0, 0, 2};
static const unsigned char other[6] = {2, 0, 0, 0, 0, 9};
static void put16(unsigned char *p, unsigned v) { p[0] = v; p[1] = v >> 8; }

/* Runtime 18's descriptor bytes and group set, then a native header and `body` bytes. */
static size_t build(unsigned char *p, unsigned groups, unsigned fc, const unsigned char *da, const unsigned char *ta, const unsigned char *bssid, size_t body)
{
 size_t off = 16, n;
 memset(p, 0, 512);
 put16(p + 2, 0xe001 | groups << 9);
 p[4] = 0x02; p[5] = 40; p[6] = 24; p[7] = 0x04; p[8] = 1; p[9] = 0; put16(p + 10, 0xe000);
 if (groups & 8) off += 16;
 if (groups & 1) off += 16;
 if (groups & 2) off += 8;
 if (groups & 4) off += 24;
 put16(p + off, fc);
 memcpy(p + off + 4, da, 6); memcpy(p + off + 10, ta, 6); memcpy(p + off + 16, bssid, 6);
 n = off + 24 + body;
 put16(p, n);
 return n;
}

static bool run(const unsigned char *src, size_t n, struct mt6797_join_action_frame *out)
{
 unsigned char *p = malloc(n ? n : 1); assert(p); memcpy(p, src, n);
 memset(out, 0x5a, sizeof(*out));
 bool ok = mt6797_join_action_frame(p, n, 40, own, ap, out);
 free(p); return ok;
}

int main(void)
{
 unsigned char p[512];
 struct mt6797_join_action_frame r;
 size_t n = build(p, 7, 0x00d0, own, ap, ap, 48);
 assert(n == 136);
 assert(run(p, n, &r) && r.bytes == 72 && r.fc == 0x00d0 && r.match == 0x02 && r.wlan == 1 && r.bss == 1 && r.sec == 0 && r.status == 0xe000);
 /* Declared lengths: below the header plus the category byte refused; from there up admitted. */
 for (size_t cut = 0; cut < n; cut++) { unsigned char q[512]; memcpy(q, p, n); put16(q, cut); assert(run(q, cut, &r) == (cut >= 64 + 25)); }
 assert(!mt6797_join_action_frame(p, n, 36, own, ap, &r));
 /* Type word: data, event, other group sets refused. */
 { unsigned char q[512]; memcpy(q, p, n);
   put16(q + 2, 0x4000 | 7 << 9); assert(!run(q, n, &r)); put16(q + 2, 0xe000 | 7 << 9); assert(!run(q, n, &r));
   for (unsigned groups = 0; groups < 16; groups++) { size_t m = build(q, groups, 0x00d0, own, ap, ap, 48); assert(run(q, m, &r) == (groups == 7)); } }
 /* Descriptor bytes 4 to 11: each measured byte exact. */
 { unsigned char q[512]; memcpy(q, p, n);
   q[4] = 0x03; assert(!run(q, n, &r)); q[4] = 0x00; assert(!run(q, n, &r)); q[4] = 0x0a; assert(!run(q, n, &r)); q[4] = 0x02;
   q[6] = 24 | 0x40; assert(!run(q, n, &r)); q[6] = 0x80 | 14; assert(!run(q, n, &r)); q[6] = 26; assert(!run(q, n, &r)); q[6] = 24;
   q[7] = 0x3c; assert(!run(q, n, &r)); q[7] = 0x00; assert(!run(q, n, &r)); q[7] = 0x05; assert(!run(q, n, &r)); q[7] = 0x04;
   q[8] = 0; assert(!run(q, n, &r)); q[8] = 2; assert(!run(q, n, &r)); q[8] = 1;
   q[9] = 0x10; assert(!run(q, n, &r)); q[9] = 0x01; assert(!run(q, n, &r)); q[9] = 0;
   for (unsigned bit = 0; bit < 16; bit++) { put16(q + 10, 0xe000 ^ (1u << bit)); assert(!run(q, n, &r)); }
   put16(q + 10, 0xe000); assert(run(q, n, &r)); }
 /* Frame control: only Retry free. */
 assert(run(p, build(p, 7, 0x08d0, own, ap, ap, 48), &r));    /* retry */
 assert(!run(p, build(p, 7, 0x40d0, own, ap, ap, 48), &r));   /* protected */
 assert(!run(p, build(p, 7, 0x00e0, own, ap, ap, 48), &r));   /* action no ack */
 assert(!run(p, build(p, 7, 0x00c0, own, ap, ap, 48), &r));   /* deauthentication */
 assert(!run(p, build(p, 7, 0x00b0, own, ap, ap, 48), &r));   /* authentication */
 assert(!run(p, build(p, 7, 0x0080, own, ap, ap, 48), &r));   /* beacon */
 assert(!run(p, build(p, 7, 0x00d8, own, ap, ap, 48), &r));   /* data type with the same subtype bits */
 assert(!run(p, build(p, 7, 0x01d0, own, ap, ap, 48), &r));   /* ToDS */
 assert(!run(p, build(p, 7, 0x02d0, own, ap, ap, 48), &r));   /* FromDS */
 assert(!run(p, build(p, 7, 0x04d0, own, ap, ap, 48), &r));   /* more fragments */
 assert(!run(p, build(p, 7, 0x10d0, own, ap, ap, 48), &r));   /* power management */
 assert(!run(p, build(p, 7, 0x20d0, own, ap, ap, 48), &r));   /* more data */
 assert(!run(p, build(p, 7, 0x80d0, own, ap, ap, 48), &r));   /* order */
 /* Addressing: group or other receiver, other transmitter, other BSSID, fragment. */
 { static const unsigned char bcast[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
   assert(!run(p, build(p, 7, 0x00d0, bcast, ap, ap, 48), &r));
   assert(!run(p, build(p, 7, 0x00d0, other, ap, ap, 48), &r));
   assert(!run(p, build(p, 7, 0x00d0, own, other, ap, 48), &r));
   assert(!run(p, build(p, 7, 0x00d0, own, ap, other, 48), &r)); }
 n = build(p, 7, 0x00d0, own, ap, ap, 48); p[64 + 22] = 1; assert(!run(p, n, &r)); p[64 + 22] = 0;
 /* Minimum: header plus one body byte, which is not read. */
 n = build(p, 7, 0x00d0, own, ap, ap, 1); assert(n == 89 && run(p, n, &r) && r.bytes == 25);
 n = build(p, 7, 0x00d0, own, ap, ap, 0); assert(!run(p, n, &r));
 mt6797_join_action_frame(NULL, 136, 40, own, ap, &r); mt6797_join_action_frame(p, 136, 40, NULL, ap, &r);
 mt6797_join_action_frame(p, 136, 40, own, NULL, &r); mt6797_join_action_frame(p, 136, 40, own, ap, NULL);
 puts("action-frame: PASS (measured class named; protected, no-ack, other subtypes, flags, peers, descriptor bytes, status, groups refused)");
 return 0;
}
