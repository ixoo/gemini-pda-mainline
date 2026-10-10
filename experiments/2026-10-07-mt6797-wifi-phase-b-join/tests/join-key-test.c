/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "join-commands.h"

/* The key command payload (pinned gen3 CMD_802_11_KEY as wlanoidSetAddKey and
 * wlanoidSetRemoveKey fill it for a WPA2-PSK CCMP station) and the WPA2 BSS
 * declaration bytes. Key bytes here are fixture constants.
 */
int main(void)
{
	static const unsigned char ap[6] = {2, 0, 0, 0, 0, 2};
	static const unsigned char bc[6] = {255, 255, 255, 255, 255, 255};
	unsigned char material[16], p[MT6797_JOIN_KEY_BYTES], want[MT6797_JOIN_KEY_BYTES], bss[MT6797_JOIN_BSS_BYTES];
	unsigned i;

	for (i = 0; i < 16; i++)
		material[i] = 0x40 + i;
	/* Pairwise add: TX key, unicast, peer AP, BSS 0, CCMP 4, key 0, 16 bytes, WLAN 1, zero RSC. */
	memset(want, 0, sizeof(want));
	want[0] = 1; want[1] = 1; want[2] = 1; memcpy(want + 4, ap, 6); want[11] = 4; want[13] = 16; want[14] = 1;
	memcpy(want + 16, material, 16);
	assert(mt6797_join_key_payload(true, true, ap, 0, material, p) && !memcmp(p, want, 64));
	/* Group add: neither flag, peer AP, key id 2, WLAN index 2 (the AP
	 * station's declared broadcast entry, as the vendor allocates it and the
	 * reference run 3 shows). */
	memset(want, 0, sizeof(want));
	want[0] = 1; memcpy(want + 4, ap, 6); want[11] = 4; want[12] = 2; want[13] = 16; want[14] = 2;
	memcpy(want + 16, material, 16);
	assert(mt6797_join_key_payload(true, false, ap, 2, material, p) && !memcmp(p, want, 64));
	assert(MT6797_JOIN_BMC_WLAN_INDEX == 2 && MT6797_JOIN_RESERVED_WLAN_INDEX == 255);
	/* Removals as wlanoidSetRemoveKey fills them on the supplicant's paths:
	 * zeroed command, AddRemove 0, key id, BSS 0; the pairwise key with the
	 * AP's address, unicast type 1 and the station's WLAN index 1; the group
	 * key with a zero peer, type 0 and the reserved WLAN index 255 (the
	 * index-based deletion without an address); no TX-key flag, no algorithm,
	 * no length, no material, no RSC. */
	memset(want, 0, sizeof(want));
	want[2] = 1; memcpy(want + 4, ap, 6); want[14] = 1;
	assert(mt6797_join_key_payload(false, true, ap, 0, NULL, p) && !memcmp(p, want, 64));
	memset(want, 0, sizeof(want));
	want[12] = 1; want[14] = 255;
	assert(mt6797_join_key_payload(false, false, NULL, 1, NULL, p) && !memcmp(p, want, 64));
	/* Refusals: broadcast or zero peer on an add, key id above 3, pairwise
	 * with a key id, add without material, a pairwise removal without a peer,
	 * a group removal with a peer (the never-requested shape). */
	assert(!mt6797_join_key_payload(true, true, bc, 0, material, p));
	assert(!mt6797_join_key_payload(true, false, (const unsigned char[6]){0}, 1, material, p));
	assert(!mt6797_join_key_payload(true, false, ap, 4, material, p));
	assert(!mt6797_join_key_payload(true, true, ap, 1, material, p));
	assert(!mt6797_join_key_payload(true, false, ap, 1, NULL, p));
	assert(!mt6797_join_key_payload(true, true, NULL, 0, material, p));
	assert(!mt6797_join_key_payload(false, true, NULL, 0, NULL, p));
	assert(!mt6797_join_key_payload(false, false, ap, 1, NULL, p));
	assert(!mt6797_join_key_payload(false, false, NULL, 4, NULL, p));
	/* The RSC bytes 48..63 are zero in every shape, as the vendor sends for CCMP. */
	assert(mt6797_join_key_payload(true, false, ap, 3, material, p));
	for (i = 48; i < 64; i++)
		assert(!p[i]);
	/* BSS declaration: WPA2-PSK (7) and encryption 3 enabled (6), or open (0) and disabled (1). */
	assert(mt6797_join_bss_payload(ap, (const unsigned char *)"lab", 3, 0x3fc0, 0x0040, false, true, bss));
	assert(bss[53] == 7 && bss[54] == 6);
	assert(mt6797_join_bss_payload(ap, (const unsigned char *)"lab", 3, 0x3fc0, 0x0040, false, false, bss));
	assert(bss[53] == 0 && bss[54] == 1);
	puts("join-key: PASS (pairwise and group add and removal shapes with the declared broadcast index, refusals, zero RSC, WPA2 BSS bytes)");
	return 0;
}
