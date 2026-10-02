/* SPDX-License-Identifier: GPL-2.0-only */
#include "../../2026-10-01-mt6797-normal-sets/tests/test-compat.h"
#include <stdio.h>
#include <string.h>
#include "normal_command.h"

static void query(void)
{
	for (unsigned int role = 0; role < 2; role++) {
		unsigned char history[32] = {0}, out[20];
		struct mt6797_normal_transaction t = {0};
		struct mt6797_hif_command command;
		assert(!mt6797_normal_admit(&t, 4, 4, history));
		t.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
		assert(!mt6797_normal_prepare_scan_early_rx(&t, role, 9, out, sizeof(out), &command));
		assert(out[0] == 16 && !out[1] && !out[2] && out[3] == 0x80);
		assert(out[4] == 0xc0 && out[5] == 0xa0 && !out[6] && out[7] == 9);
		assert(out[8] == (role ? 0x3c : 0x38) && out[9] == 0xbf);
		assert(out[10] == 6 && out[11] == 0xf0);
		for (unsigned int n = 12; n < 16; n++) assert(!out[n]);
		assert(t.tc4_free == 3 && t.phase == MT6797_NORMAL_CONFIG_TX);
		assert(history[1] == 2);
		assert(!mt6797_normal_submitted(&t, 0));
		assert(t.phase == MT6797_NORMAL_NVRAM_SUBMITTED && t.tc4_free == 3);
		assert(mt6797_normal_prepare_scan_early_rx(&t, role, 9, out, sizeof(out), &command) == -EIO);
		assert(t.phase == MT6797_NORMAL_FAILED && t.tc4_free == 3);
	}
	unsigned char history[32] = {0}, out[20], before[20];
	struct mt6797_normal_transaction t = {0};
	struct mt6797_hif_command command;
	assert(!mt6797_normal_admit(&t, 1, 0, history));
	t.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	memset(out, 0xa5, sizeof(out)); memcpy(before, out, sizeof(out));
	assert(mt6797_normal_prepare_scan_early_rx(&t, 2, 1, out, sizeof(out), &command) == -EINVAL);
	assert(mt6797_normal_prepare_scan_early_rx(&t, 0, 1, out, sizeof(out), &command) == -ENOSPC);
	assert(!memcmp(out, before, sizeof(out)) && !history[0] && !t.tc4_free);
	t.tc4_free = 1;
	assert(mt6797_normal_prepare_scan_early_rx(&t, 0, 1, out, 15, &command));
	assert(!memcmp(out, before, sizeof(out)) && !history[0] && t.tc4_free == 1);
	assert(!mt6797_normal_prepare_scan_early_rx(&t, 0, 1, out, sizeof(out), &command));
	assert(mt6797_normal_submitted(&t, -EIO) == -EIO);
	assert(t.phase == MT6797_NORMAL_FAILED && !t.tc4_free);
}
static void reply(void)
{
	for (unsigned int role = 0; role < 2; role++) {
		unsigned int value, address = mt6797_scan_early_rx_address(role);
		unsigned char packet[17] = {16, 0, 0, 0xe0, 5, 9};
		for (unsigned int n = 0; n < 4; n++) packet[8 + n] = address >> (8 * n);
		packet[12] = 0x40; packet[13] = 0x4b; packet[14] = 0x4c;
		assert(!mt6797_scan_early_rx_reply(packet, 16, role, 9, &value));
		assert(value == 5000000);
		for (unsigned int n = 0; n < 4; n++)
			packet[8 + n] = 0xf006c040U >> (8 * n);
		assert(mt6797_scan_early_rx_reply(packet, 16, role, 9, &value) == -EPROTO);
		for (unsigned int n = 0; n < 4; n++)
			packet[8 + n] = 0xf006bf7cU >> (8 * n);
		assert(mt6797_scan_early_rx_reply(packet, 16, role, 9, &value) == -EPROTO);
		for (unsigned int n = 0; n < 4; n++)
			packet[8 + n] = address >> (8 * n);
		for (unsigned int n = 0; n <= 17; n++) {
			if (n == 16) continue;
			assert(mt6797_scan_early_rx_reply(packet, n, role, 9, &value) == -EPROTO);
			assert(!value);
		}
		for (unsigned int n = 0; n < 12; n++) {
			if (n == 6 || n == 7) continue; /* unspecified reserved fields */
			packet[n] ^= 1;
			assert(mt6797_scan_early_rx_reply(packet, 16, role, 9, &value) == -EPROTO);
			assert(!value); packet[n] ^= 1;
		}
		assert(mt6797_scan_early_rx_reply(packet, 16, 1 - role, 9, &value) == -EPROTO);
		assert(mt6797_scan_early_rx_reply(packet, 16, role, 10, &value) == -EPROTO);
	}
}
int main(void) { query(); reply(); puts("scan early_rx wire tests: PASS"); }
