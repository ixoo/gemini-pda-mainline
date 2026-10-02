/* SPDX-License-Identifier: GPL-2.0-only */
#include "../../2026-10-01-mt6797-normal-sets/tests/test-compat.h"
#include <stdio.h>
#include <string.h>
#include "normal_command.h"

static void init(struct mt6797_normal_transaction *t, unsigned char *history)
{
	*t = (struct mt6797_normal_transaction){0};
	memset(history, 0, 32);
	assert(!mt6797_normal_admit(t, 26, 25, history));
	t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
}
int main(void)
{
	unsigned char history[32], payload[4] = {8}, frame[16], before[16];
	struct mt6797_normal_transaction t = {0};
	struct mt6797_hif_command cmd;
	for (unsigned int n = 0; n < 256; n++) {
		init(&t, history); payload[0] = n;
		memset(frame, 0xa5, sizeof(frame)); memcpy(before, frame, sizeof(frame));
		int ret = mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_BROADCAST,
			5, payload, 4, frame, sizeof(frame), &cmd);
		if (n != 8) {
			assert(ret == -EINVAL && t.tc4_free == 25 && !history[0]);
			assert(!memcmp(frame, before, sizeof(frame)));
			continue;
		}
		assert(!ret && t.tc4_free == 24 && history[0] == 32);
		assert(frame[0] == 12 && !frame[1] && frame[3] == 0x80);
		assert(frame[4] == 0x0a && frame[5] == 0xa0 && frame[6] == 1 && frame[7] == 5);
		assert(frame[8] == 8 && !frame[9] && !frame[10] && !frame[11]);
		assert(!mt6797_normal_submitted(&t, 0));
		assert(t.phase == MT6797_NORMAL_NVRAM_SUBMITTED);
		assert(mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_BROADCAST,
			5, payload, 4, frame, sizeof(frame), &cmd) < 0);
	}
	payload[0] = 8;
	for (unsigned int n = 0; n < 8; n++) if (n != 4) {
		init(&t, history);
		assert(mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_BROADCAST,
			5, payload, n, frame, sizeof(frame), &cmd) == -EINVAL);
		assert(t.tc4_free == 25 && !history[0]);
	}
	for (unsigned int n = 1; n < 4; n++) {
		init(&t, history); payload[n] = 1;
		assert(mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_BROADCAST,
			5, payload, 4, frame, sizeof(frame), &cmd) == -EINVAL);
		payload[n] = 0;
	}
	init(&t, history); t.phase = MT6797_NORMAL_CAP_RECEIVED;
	assert(mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_BROADCAST,
		5, payload, 4, frame, sizeof(frame), &cmd) < 0);
	init(&t, history);
	assert(!mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_BROADCAST,
		5, payload, 4, frame, sizeof(frame), &cmd));
	assert(mt6797_normal_submitted(&t, -EIO) < 0);
	assert(t.phase == MT6797_NORMAL_FAILED);
	puts("broadcast_filter_contract=pass");
}
