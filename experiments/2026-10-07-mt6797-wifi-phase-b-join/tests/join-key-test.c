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
	/* Group add: neither flag, peer AP, key id 2, WLAN index 0 (BMC). */
	memset(want, 0, sizeof(want));
	want[0] = 1; memcpy(want + 4, ap, 6); want[11] = 4; want[12] = 2; want[13] = 16; want[14] = 0;
	memcpy(want + 16, material, 16);
	assert(mt6797_join_key_payload(true, false, ap, 2, material, p) && !memcmp(p, want, 64));
	/* Removals as wlanoidSetRemoveKey fills them: zeroed command, AddRemove 0,
	 * key id, peer, BSS 0; unicast type 1 with the station's WLAN index 1 for
	 * the pairwise key; type 0 with the declared BMC index 0 for the group
	 * key; no TX-key flag, no algorithm, no length, no material, no RSC. */
	memset(want, 0, sizeof(want));
	want[2] = 1; memcpy(want + 4, ap, 6); want[14] = 1;
	assert(mt6797_join_key_payload(false, true, ap, 0, NULL, p) && !memcmp(p, want, 64));
	memset(want, 0, sizeof(want));
	memcpy(want + 4, ap, 6); want[12] = 1;
	assert(mt6797_join_key_payload(false, false, ap, 1, NULL, p) && !memcmp(p, want, 64));
	/* Refusals: broadcast or zero peer, key id above 3, pairwise with a key id, add without material. */
	assert(!mt6797_join_key_payload(true, true, bc, 0, material, p));
	assert(!mt6797_join_key_payload(true, false, (const unsigned char[6]){0}, 1, material, p));
	assert(!mt6797_join_key_payload(true, false, ap, 4, material, p));
	assert(!mt6797_join_key_payload(true, true, ap, 1, material, p));
	assert(!mt6797_join_key_payload(true, false, ap, 1, NULL, p));
	assert(!mt6797_join_key_payload(true, true, NULL, 0, material, p));
	/* The RSC bytes 48..63 are zero in every shape, as the vendor sends for CCMP. */
	assert(mt6797_join_key_payload(true, false, ap, 3, material, p));
	for (i = 48; i < 64; i++)
		assert(!p[i]);
	/* BSS declaration: WPA2-PSK (7) and encryption 3 enabled (6), or open (0) and disabled (1). */
	assert(mt6797_join_bss_payload(ap, (const unsigned char *)"lab", 3, 0x3fc0, 0x0040, false, true, bss));
	assert(bss[53] == 7 && bss[54] == 6);
	assert(mt6797_join_bss_payload(ap, (const unsigned char *)"lab", 3, 0x3fc0, 0x0040, false, false, bss));
	assert(bss[53] == 0 && bss[54] == 1);
	puts("join-key: PASS (pairwise and group add and removal shapes, refusals, zero RSC, WPA2 BSS bytes)");
	return 0;
}
