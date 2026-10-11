/* SPDX-License-Identifier: GPL-2.0-only */
/* The directed clear Action frame decoder: exactly the measured class of
 * runtime 18 is named (logged metadata: 136 bytes, type word exactly 0xee01,
 * descriptor bytes 02 28 18 04 01 00 00 e0, frame control
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
/* The caller's key state (true once the pairwise key is installed) and the
 * descriptor variant the builder writes: runtime 18's (byte 9 = 0, status 0xe000)
 * or runtime 24's (0x40, 0xe004). The unkeyed variant is the class in both states;
 * the keyed variant only in the keyed state. */
static bool keyed = false, variant_keyed = false;

/* Runtime 18's descriptor bytes and group set, then a native header and `body` bytes. */
static size_t build(unsigned char *p, unsigned groups, unsigned fc, const unsigned char *da, const unsigned char *ta, const unsigned char *bssid, size_t body)
{
 size_t off = 16, n;
 memset(p, 0, 1024);
 put16(p + 2, 0xe001 | groups << 9);
 p[4] = 0x02; p[5] = 40; p[6] = 24; p[7] = 0x04; p[8] = 1; p[9] = variant_keyed ? 0x40 : 0; put16(p + 10, variant_keyed ? 0xe004 : 0xe000);
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
 bool ok = mt6797_join_action_frame(p, n, 40, own, ap, keyed, out);
 free(p); return ok;
}

int main(void)
{
 unsigned char p[1024];
 struct mt6797_join_action_frame r;
 size_t n = build(p, 7, 0x00d0, own, ap, ap, 48);
 assert(n == 136);
 assert(run(p, n, &r) && r.bytes == 72 && r.fc == 0x00d0 && r.match == 0x02 && r.wlan == 1 && r.bss == 1 && r.sec == 0 && r.status == 0xe000);
 /* Declared lengths: below the header plus two body bytes refused; from there up admitted. */
 for (size_t cut = 0; cut < n; cut++) { unsigned char q[1024]; memcpy(q, p, n); put16(q, cut); assert(run(q, cut, &r) == (cut >= 64 + 26)); }
 assert(!mt6797_join_action_frame(p, n, 36, own, ap, keyed, &r));
 /* Type word exactly 0xee01: every single-bit flip, data and event type words,
  * and every other group set refused. */
 { unsigned char q[1024]; memcpy(q, p, n);
   for (unsigned bit = 0; bit < 16; bit++) { put16(q + 2, 0xee01 ^ (1u << bit)); assert(!run(q, n, &r)); }
   put16(q + 2, 0x4000 | 7 << 9); assert(!run(q, n, &r)); put16(q + 2, 0xe000 | 7 << 9); assert(!run(q, n, &r));
   put16(q + 2, 0xee01); assert(run(q, n, &r));
   for (unsigned groups = 0; groups < 16; groups++) { size_t m = build(q, groups, 0x00d0, own, ap, ap, 48); assert(run(q, m, &r) == (groups == 7)); } }
 /* Descriptor bytes 4 to 11: each measured byte exact. */
 { unsigned char q[1024]; memcpy(q, p, n);
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
 /* Minimum: header plus two body bytes (category and one more), none read; one byte short refused. */
 n = build(p, 7, 0x00d0, own, ap, ap, 2); assert(n == 90 && run(p, n, &r) && r.bytes == 26);
 n = build(p, 7, 0x00d0, own, ap, ap, 1); assert(n == 89 && !run(p, n, &r));
 n = build(p, 7, 0x00d0, own, ap, ap, 0); assert(!run(p, n, &r));
 mt6797_join_action_frame(NULL, 136, 40, own, ap, keyed, &r); mt6797_join_action_frame(p, 136, 40, NULL, ap, keyed, &r);
 mt6797_join_action_frame(p, 136, 40, own, NULL, keyed, &r); mt6797_join_action_frame(p, 136, 40, own, ap, keyed, NULL);
 /* Runtime 24's keyed descriptor variant of the same source-defined class (bytes
  * 02 28 18 04 01 40 04 e0, 136 bytes, frame control 0x00d0, receiver this station,
  * transmitter the target): admitted only in the keyed state; the unkeyed variant
  * stays admitted in both states; mixed cipher/status pairs, the ICV-error flag, other
  * modes, a TID, a protected frame control and other peers are refused in both states. */
 keyed = true; variant_keyed = true;
 n = build(p, 7, 0x00d0, own, ap, ap, 48);
 assert(n == 136 && p[9] == 0x40 && run(p, n, &r) && r.bytes == 72 && r.fc == 0x00d0 && r.match == 0x02 && r.wlan == 1 && r.bss == 1 && r.sec == 4 && r.status == 0xe004);
 assert(!mt6797_join_action_frame(p, n, 40, own, ap, false, &r));                                 /* keyed variant before the key */
 { unsigned char q[1024]; memcpy(q, p, n);
   q[9] = 0; assert(!run(q, n, &r)); q[9] = 0x40; put16(q + 10, 0xe000); assert(!run(q, n, &r));   /* mixed pairs */
   put16(q + 10, 0xe014); assert(!run(q, n, &r)); put16(q + 10, 0xe010); assert(!run(q, n, &r)); /* ICV error */
   put16(q + 10, 0xe00c); assert(!run(q, n, &r)); put16(q + 10, 0xc004); assert(!run(q, n, &r));
   put16(q + 10, 0xe004); q[9] = 0x44; assert(!run(q, n, &r)); q[9] = 0x10; assert(!run(q, n, &r)); q[9] = 0x40; /* TID, another mode */
   assert(run(q, n, &r)); }
 assert(!run(p, build(p, 7, 0x40d0, own, ap, ap, 48), &r));                                       /* protected */
 assert(!run(p, build(p, 7, 0x00e0, own, ap, ap, 48), &r));                                       /* Action No Ack */
 assert(!run(p, build(p, 7, 0x00d0, own, other, ap, 48), &r));                                    /* another transmitter */
 assert(!run(p, build(p, 7, 0x00d0, ap, ap, ap, 48), &r));                                        /* another receiver */
 n = build(p, 7, 0x00d0, own, ap, ap, 48); p[4] = 0x08; assert(!run(p, n, &r)); p[4] = 0x02; p[8] = 255; assert(!run(p, n, &r));
 variant_keyed = false;
 n = build(p, 7, 0x00d0, own, ap, ap, 48); assert(p[9] == 0 && run(p, n, &r) && r.sec == 0 && r.status == 0xe000); /* unkeyed variant after the key: still the class */
 keyed = false;
 n = build(p, 7, 0x00d0, own, ap, ap, 48); assert(run(p, n, &r) && r.sec == 0 && r.status == 0xe000);               /* and before it */
 { unsigned char q[1024]; memcpy(q, p, n); q[9] = 0x40; put16(q + 10, 0xe004); assert(!run(q, n, &r)); }            /* keyed variant before the key */

 /* Runtime 21's class: broadcast match 0x08, descriptor bytes 18 3c ff 00 00 e0, clear Action
  * to the broadcast address, 644 wire bytes (708 in all); the transmitter and BSSID are not
  * compared. Observed-field and source-defined-field perturbations are refused. */
 { static const unsigned char bcast[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
   struct mt6797_join_action_frame g;
   size_t m;
   #define GBUILD(groups, fc, da, body) do { m = build(p, groups, fc, da, other, other, body); p[4] = 0x08; p[7] = 0x3c; p[8] = 255; } while (0)
   #define GRUN() (memset(&g, 0x5a, sizeof(g)), mt6797_join_group_action_frame(p, m, 40, &g))
   GBUILD(7, 0x00d0, bcast, 620); assert(m == 708 && GRUN() && g.bytes == 644 && g.fc == 0x00d0 && g.match == 0x08 && g.wlan == 255 && g.bss == 15 && g.sec == 0 && g.status == 0xe000);
   GBUILD(7, 0x08d0, bcast, 620); assert(GRUN() && g.fc == 0x08d0);                      /* a retry */
   GBUILD(7, 0x00d0, bcast, 2); assert(m == 90 && GRUN() && g.bytes == 26);              /* minimum body */
   GBUILD(7, 0x00d0, bcast, 1); assert(!GRUN());
   GBUILD(7, 0x00d0, bcast, 620); memcpy(p + 64 + 10, ap, 6); memcpy(p + 64 + 16, ap, 6); assert(GRUN()); /* the target as transmitter: not compared */
   GBUILD(7, 0x00d0, bcast, 620); p[4] = 0x04; assert(!GRUN());                           /* multicast bit: not observed */
   GBUILD(7, 0x00d0, bcast, 620); p[4] = 0x02; assert(!GRUN());                           /* unicast-to-me */
   GBUILD(7, 0x00d0, bcast, 620); p[4] = 0x0a; assert(!GRUN());
   GBUILD(7, 0x00d0, bcast, 620); p[8] = 1; assert(!GRUN());                              /* a WLAN table entry */
   GBUILD(7, 0x00d0, bcast, 620); p[8] = 31; assert(!GRUN());
   GBUILD(7, 0x00d0, bcast, 620); p[7] = 0x04; assert(!GRUN());                           /* BSSID field 1 */
   GBUILD(7, 0x00d0, bcast, 620); p[6] = 0x80 | 24; assert(!GRUN());                      /* translated */
   GBUILD(7, 0x00d0, bcast, 620); p[9] = 0x40; assert(!GRUN());                           /* security mode */
   GBUILD(7, 0x00d0, bcast, 620); put16(p + 10, 0xc000); assert(!GRUN());
   GBUILD(7, 0x40d0, bcast, 620); assert(!GRUN());                                        /* protected */
   GBUILD(7, 0x00e0, bcast, 620); assert(!GRUN());                                        /* Action No Ack */
   GBUILD(7, 0x00c0, bcast, 620); assert(!GRUN());                                        /* deauthentication */
   GBUILD(7, 0x00d0, own, 620); assert(!GRUN());                                          /* directed */
   { static const unsigned char mc[6] = {0x01, 0x00, 0x5e, 0, 0, 1}; GBUILD(7, 0x00d0, mc, 620); assert(!GRUN()); } /* multicast receiver */
   GBUILD(7, 0x00d0, bcast, 620); p[64 + 22] = 1; assert(!GRUN());                       /* fragment */
   GBUILD(15, 0x00d0, bcast, 620); assert(!GRUN());                                       /* group 4 present: another type word */
   GBUILD(7, 0x00d0, bcast, 620); p[5] = 36; assert(!GRUN());
   GBUILD(7, 0x00d0, bcast, 620); put16(p, m + 1); assert(!GRUN());
   assert(!mt6797_join_group_action_frame(NULL, 708, 40, &g) && !mt6797_join_group_action_frame(p, 708, 0, &g) && !mt6797_join_group_action_frame(p, 708, 40, NULL));
   /* Neither decoder admits the other's class. */
   GBUILD(7, 0x00d0, bcast, 620); assert(!run(p, m, &r));
   m = build(p, 7, 0x00d0, own, ap, ap, 48); assert(!GRUN());
   #undef GBUILD
   #undef GRUN
 }
 /* Runtime 26's keyed beacon variant (descriptor bytes 08 28 18 04 02 40 04 e0, 442 bytes,
  * frame control 0x0080, broadcast receiver, the target as transmitter and BSSID): named
  * only with the declared broadcast entry; the unkeyed descriptor, mixed pairs, the
  * ICV-error flag, a probe response, other peers, other indices and a short body refused. */
 { static const unsigned char bcast[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
   struct mt6797_join_action_frame k;
   size_t m;
   #define KBUILD(fc, da, ta, bssid, body) do { m = build(p, 7, fc, da, ta, bssid, body); p[4] = 0x08; p[7] = 0x04; p[8] = 2; p[9] = 0x40; put16(p + 10, 0xe004); } while (0)
   #define KRUN(bmc) (memset(&k, 0x5a, sizeof(k)), mt6797_join_keyed_beacon(p, m, 40, ap, (bmc), &k))
   KBUILD(0x0080, bcast, ap, ap, 354); assert(m == 442 && KRUN(2) && k.bytes == 378 && k.fc == 0x0080 && k.match == 0x08 && k.wlan == 2 && k.bss == 1 && k.sec == 4 && k.status == 0xe004);
   assert(!KRUN(0) && !KRUN(1));                                                            /* another declared entry */
   KBUILD(0x0080, bcast, ap, ap, 12); assert(KRUN(2) && k.bytes == 36);                    /* the fixed body only */
   KBUILD(0x0080, bcast, ap, ap, 11); assert(!KRUN(2));
   KBUILD(0x0080, bcast, ap, ap, 354); p[9] = 0; assert(!KRUN(2)); p[9] = 0x40; put16(p + 10, 0xe000); assert(!KRUN(2)); /* unkeyed descriptor, mixed pairs */
   put16(p + 10, 0xe014); assert(!KRUN(2)); put16(p + 10, 0xe010); assert(!KRUN(2)); put16(p + 10, 0xc004); assert(!KRUN(2));
   put16(p + 10, 0xe004); p[8] = 1; assert(!KRUN(2)); p[8] = 255; assert(!KRUN(2)); p[8] = 2;                               /* other indices */
   p[4] = 0x02; assert(!KRUN(2)); p[4] = 0x0c; assert(!KRUN(2)); p[4] = 0x08;                                              /* other match flags */
   p[7] = 0x3c; assert(!KRUN(2)); p[7] = 0x04; p[6] = 0x80 | 24; assert(!KRUN(2)); p[6] = 24; assert(KRUN(2));
   KBUILD(0x0050, bcast, ap, ap, 354); assert(!KRUN(2));                                    /* probe response */
   KBUILD(0x0880, bcast, ap, ap, 354); assert(!KRUN(2));                                    /* Retry */
   KBUILD(0x4080, bcast, ap, ap, 354); assert(!KRUN(2));                                    /* protected */
   KBUILD(0x00d0, bcast, ap, ap, 354); assert(!KRUN(2));                                    /* Action */
   KBUILD(0x0080, own, ap, ap, 354); assert(!KRUN(2));                                      /* directed */
   KBUILD(0x0080, bcast, other, ap, 354); assert(!KRUN(2));                                 /* another transmitter */
   KBUILD(0x0080, bcast, ap, other, 354); assert(!KRUN(2));                                 /* another BSSID */
   KBUILD(0x0080, bcast, ap, ap, 354); p[64 + 22] = 1; assert(!KRUN(2)); p[64 + 22] = 0; p[5] = 36; assert(!KRUN(2)); p[5] = 40;
   put16(p + 2, 0xe001 | 15 << 9); assert(!KRUN(2));                                        /* another group set: another type word */
   assert(!mt6797_join_keyed_beacon(NULL, 442, 40, ap, 2, &k) && !mt6797_join_keyed_beacon(p, 442, 40, NULL, 2, &k) && !mt6797_join_keyed_beacon(p, 442, 40, ap, 2, NULL));
   /* Neither Action decoder admits the beacon and the beacon decoder admits no Action frame. */
   KBUILD(0x0080, bcast, ap, ap, 354); assert(!run(p, m, &r) && !mt6797_join_group_action_frame(p, m, 40, &r));
   m = build(p, 7, 0x00d0, own, ap, ap, 48); assert(!KRUN(2));
   #undef KBUILD
   #undef KRUN
 }

 puts("action-frame: PASS (measured class named; protected, no-ack, other subtypes, flags, peers, descriptor bytes, status, groups refused; runtime 21 broadcast class named; runtime 24 keyed variant admitted only after the pairwise key, the unkeyed variant kept; runtime 26 keyed beacon named under the declared entry)");
 return 0;
}
