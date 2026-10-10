/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "data-rx.h"

/* Synthetic boundary and malformed cases for the protected translated data
 * decoder: the two source-defined non-aggregated classes (unicast on WLAN
 * index 1, group on the declared broadcast entry), rebuilt header bytes, and
 * every refusal: aggregated status (either A-MPDU bit clear, the pinned
 * inverse polarity), error bits, QoS or other frame controls, missing group
 * 4, wrong WLAN index, wrong security mode, wrong BSSID field, wrong channel,
 * untranslated header, group source, foreign transmitter, short payload,
 * EAPOL type passes the decoder (the caller refuses it). Bytes are fixture
 * constants; no packet of the reference is replayed.
 */
static const unsigned char own[6] = {2, 0, 0, 0, 0, 1}, ap[6] = {2, 0, 0, 0, 0, 2};
static const unsigned char host[6] = {2, 0, 0, 0, 0, 3}, bcast[6] = {255, 255, 255, 255, 255, 255};

static size_t build(unsigned char *p, bool group, bool vector, unsigned int payload)
{
	size_t at = 16, total;
	unsigned int type;

	memset(p, 0, 256);
	type = 2U << 13 | (vector ? 0xc : 0x8) << 9; /* data, group 4 (+ group 3) present */
	p[2] = type; p[3] = type >> 8;
	p[4] = group ? 0x08 : 0x02; /* BC, or unicast-to-me */
	p[5] = 40;
	p[6] = 0x80 | 14; /* translated, 14-byte header, no offset pad */
	p[7] = 0x04;      /* MSDU format, BSSID field 1 */
	p[8] = group ? 2 : 1;
	p[9] = 4 << 4;    /* CCMP, TID 0 */
	p[10] = 0x00; p[11] = 0xc0;
	/* group 4: fc 0x4208 (data, FromDS, protected), transmitter, seq 0x0120 */
	p[at] = 0x08; p[at + 1] = 0x42; memcpy(p + at + 2, ap, 6); p[at + 8] = 0x20; p[at + 9] = 0x01;
	at += 16;
	if (vector) {
		p[at + 9] = 100; /* RCPI 100 -> -60 dBm */
		at += 24;
	}
	memcpy(p + at, group ? bcast : own, 6);
	memcpy(p + at + 6, host, 6);
	p[at + 12] = 0x08; p[at + 13] = 0x00; /* IPv4 */
	total = at + 14 + payload;
	p[0] = total; p[1] = total >> 8;
	return total;
}

int main(void)
{
	unsigned char p[256];
	struct mt6797_data_rx r;
	size_t n;
	unsigned int i;

	/* Unicast with the RX vector: header rebuilt, payload located, signal valid. */
	n = build(p, false, true, 20);
	assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	assert(!r.group && r.ether_type == 0x0800 && r.tid == 0 && r.key_id == 0);
	assert(r.offset == 16 + 16 + 24 + 14 && r.bytes == 20 && r.signal_valid && r.signal_dbm == -60);
	assert(r.prefix[0] == 0x08 && r.prefix[1] == 0x42 && !r.prefix[2] && !r.prefix[3]);
	assert(!memcmp(r.prefix + 4, own, 6) && !memcmp(r.prefix + 10, ap, 6) && !memcmp(r.prefix + 16, host, 6));
	assert(r.prefix[22] == 0x20 && r.prefix[23] == 0x01);
	assert(r.prefix[24] == 0xaa && r.prefix[25] == 0xaa && r.prefix[26] == 3 && !r.prefix[27] && !r.prefix[28] &&
	       !r.prefix[29] && r.prefix[30] == 0x08 && !r.prefix[31]);
	/* Group on the declared broadcast entry, without the vector: signal invalid. */
	n = build(p, true, false, 40);
	assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	assert(r.group && !r.signal_valid && r.offset == 16 + 16 + 14 && r.bytes == 40 && !memcmp(r.prefix + 4, bcast, 6));
	assert(!mt6797_data_rx(p, n, 40, own, ap, 0, &r)); /* another declared entry */
	/* Multicast match bit with a multicast destination. */
	p[4] = 0x04; p[16 + 16] = 0x01; p[16 + 17] = 0x00; p[16 + 18] = 0x5e;
	assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r) && r.group);
	/* Key id bits are recorded, never a refusal. */
	n = build(p, false, false, 20); p[4] |= 1 << 6;
	assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r) && r.key_id == 1);
	/* Retry and More Data are free (as in the EAPOL decoder); Power Management
	 * and everything else refused. */
	n = build(p, false, false, 20);
	p[16 + 1] = 0x42 | 0x08; assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r));           /* retry */
	p[16 + 1] = 0x42 | 0x20; assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r));           /* more data */
	p[16 + 1] = 0x42 | 0x10; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));          /* power management */
	p[16 + 1] = 0x42; p[16] = 0x88; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));   /* QoS data */
	p[16] = 0x08 | 0x01; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[16] = 0x08; /* ToDS */
	p[16 + 1] = 0x02; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));                 /* not protected */
	p[16 + 1] = 0x42 | 0x04; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));          /* more fragments */
	p[16 + 1] = 0x42 | 0x80; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));          /* order */
	p[16 + 1] = 0x42; p[16] = 0x48; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[16] = 0x08; /* null data */
	p[16 + 8] = 0x21; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[16 + 8] = 0x20; /* fragment 1 */
	assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	/* Status word: aggregated (either A-MPDU bit clear) and every error bit refused. */
	for (i = 0; i < 16; i++) {
		unsigned int status = 0xc000 ^ (1U << i);

		p[10] = status; p[11] = status >> 8;
		assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	}
	p[10] = 0; p[11] = 0; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); /* the reference's aggregated unicast */
	p[10] = 0x00; p[11] = 0xc0; assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	/* Descriptor fields: WLAN index, security mode, BSSID field, channel, translation, header length. */
	p[8] = 2; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[8] = 1;
	p[9] = 0x30; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[9] = 0x40;
	p[9] = 0x45; assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r) && r.tid == 5); p[9] = 0x40;
	p[7] = 0x3c; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[7] = 0x04;
	assert(!mt6797_data_rx(p, n, 36, own, ap, 2, &r));
	p[6] = 14; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[6] = 0x80 | 14;
	p[6] = 0x80 | 24; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[6] = 0x80 | 14;
	p[4] = 0x0a; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); /* unicast-to-me with the broadcast bit */
	p[4] = 0x00; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[4] = 0x02;
	/* Addresses: foreign transmitter, group source, unicast not to this station, group without the bit. */
	p[16 + 2] ^= 1; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[16 + 2] ^= 1;
	p[32 + 6] |= 1; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[32 + 6] &= ~1;
	p[32] ^= 2; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r)); p[32] ^= 2;
	n = build(p, true, false, 20); p[32] = 2; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	/* Missing group 4, declared length, short frames, header offset pad. */
	n = build(p, false, false, 20); p[3] = (2U << 13 | 0) >> 8; p[2] = 0;
	assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	n = build(p, false, false, 20);
	for (i = 0; i < n; i++)
		assert(!mt6797_data_rx(p, i, 40, own, ap, 2, &r));
	n = build(p, false, false, 0); assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r) && r.bytes == 0);
	n = build(p, false, false, 0); p[0] = n - 1; assert(!mt6797_data_rx(p, n - 1, 40, own, ap, 2, &r));
	n = build(p, false, false, 20); memmove(p + 34, p + 32, 14 + 20); p[6] |= 0x40; p[0] = n + 2;
	assert(mt6797_data_rx(p, n + 2, 40, own, ap, 2, &r) && r.offset == 16 + 16 + 2 + 14 && r.bytes == 20);
	/* RCPI above 220 is refused as in the other decoders. */
	n = build(p, false, true, 20); p[16 + 16 + 9] = 221; assert(!mt6797_data_rx(p, n, 40, own, ap, 2, &r));
	/* EAPOL type passes the decoder; the caller refuses it (no rekey). */
	n = build(p, false, false, 99); p[32 + 12] = 0x88; p[32 + 13] = 0x8e;
	assert(mt6797_data_rx(p, n, 40, own, ap, 2, &r) && r.ether_type == 0x888e);
	assert(!mt6797_data_rx(NULL, n, 40, own, ap, 2, &r) && !mt6797_data_rx(p, n, 40, NULL, ap, 2, &r) &&
	       !mt6797_data_rx(p, n, 40, own, NULL, 2, &r) && !mt6797_data_rx(p, n, 40, own, ap, 2, NULL));
	puts("data-rx: PASS (two non-aggregated classes, rebuilt header, aggregated/QoS/error/field/address/length refusals)");
	return 0;
}
