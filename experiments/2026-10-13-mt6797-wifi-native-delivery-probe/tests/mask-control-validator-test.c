// SPDX-License-Identifier: GPL-2.0-only
/* Actual command admission: fixed diagnostic payload, no generic register API. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "join-command-submit.h"

static void reset(struct mt6797_normal_transaction *t, unsigned char history[32])
{
	memset(t, 0, sizeof(*t)); memset(history, 0, 32);
	assert(!mt6797_normal_admit(t, 4, 4, history));
	t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
}

int main(void)
{
	struct mt6797_normal_transaction t;
	struct mt6797_hif_command cmd;
	unsigned char history[32], output[64], p[16] = {0};
#ifdef CONFIG_MT6797_CCMP_MASK_CONTROL
	struct mt6797_normal_transaction before;
	unsigned char saved[64];

	assert(!mt6797_diag_mask_payload(true, NULL));
	for (unsigned int enable = 0; enable < 2; enable++) {
		assert(mt6797_diag_mask_payload(enable, p));
		reset(&t, history);
		assert(!mt6797_join_prepare_command(&t, 0xc0, 19, p, 8,
						  output, sizeof(output), &cmd));
		const unsigned char header[8] = {16, 0, 0, 0x80, 0xc0, 0xa0, 1, 19};
		assert(!memcmp(output, header, 8));
		const unsigned char payload[8] = {0x68, 0, 0x0c, 0x80, enable ? 7 : 0, 0, 0, 0};
		assert(!memcmp(output + 8, payload, 8));
		assert(t.tc4_free == 3 && t.phase == MT6797_NORMAL_CONFIG_TX);
		assert(t.config_return_phase == MT6797_NORMAL_NVRAM_SUBMITTED);
		assert(history[2] == 8);
		for (unsigned int byte = 0; byte < 8; byte++)
			for (unsigned int bit = 0; bit < 8; bit++) {
				unsigned char bad[8]; memcpy(bad, p, 8); bad[byte] ^= 1U << bit;
				reset(&t, history); before = t; memset(output, 0xa5, sizeof(output));
				memcpy(saved, output, sizeof(output));
				assert(mt6797_join_prepare_command(&t, 0xc0, 19, bad, 8,
					output, sizeof(output), &cmd) == -EINVAL);
				assert(!memcmp(&t, &before, sizeof(t)) && !memcmp(output, saved, sizeof(output)));
			}
		/* ASan allocation boundaries: reject size before reading payload. */
		for (unsigned int size = 0; size <= 9; size++) {
			if (size == 8) continue;
			unsigned char *short_p = malloc(size ? size : 1); assert(short_p);
			reset(&t, history); before = t;
			assert(mt6797_join_prepare_command(&t, 0xc0, 19, short_p, size,
				output, sizeof(output), &cmd) == -EINVAL);
			assert(!memcmp(&t, &before, sizeof(t))); free(short_p);
		}
		for (unsigned int value = 1; value < 256; value++) {
			if (value == 7) continue;
			p[4] = value; reset(&t, history);
			assert(mt6797_join_prepare_command(&t, 0xc0, 19, p, 8,
				output, sizeof(output), &cmd) == -EINVAL);
		}
		assert(mt6797_diag_mask_payload(enable, p));
		reset(&t, history); t.tc4_free = 3; before = t;
		assert(mt6797_join_prepare_command(&t, 0xc0, 19, p, 8,
			output, sizeof(output), &cmd) == -EBUSY);
		assert(!memcmp(&t, &before, sizeof(t)));
		for (unsigned int seq = 0; seq <= 256; seq += 256) {
			reset(&t, history);
			assert(mt6797_join_prepare_command(&t, 0xc0, seq, p, 8,
				output, sizeof(output), &cmd) == -EINVAL);
		}
		reset(&t, history); history[2] = 8;
		assert(mt6797_join_prepare_command(&t, 0xc0, 19, p, 8,
			output, sizeof(output), &cmd) != 0);
	}
#else
	reset(&t, history);
	assert(mt6797_join_prepare_command(&t, 0xc0, 19, p, 8,
		output, sizeof(output), &cmd) == -EINVAL);
#endif
	/* The global monitor operation must not be a fallback in the new mode. */
	memset(p, 0, sizeof(p)); p[2] = 40;
	reset(&t, history);
#ifdef CONFIG_MT6797_CCMP_MASK_CONTROL
	assert(mt6797_join_prepare_command(&t, 0xfc, 19, p, 16,
		output, sizeof(output), &cmd) == -EINVAL);
#elif defined(CONFIG_MT6797_NATIVE_DELIVERY_DIAG)
	assert(!mt6797_join_prepare_command(&t, 0xfc, 19, p, 16,
		output, sizeof(output), &cmd));
#else
	assert(mt6797_join_prepare_command(&t, 0xfc, 19, p, 16,
		output, sizeof(output), &cmd) == -EINVAL);
#endif
	reset(&t, history); memset(p, 0, sizeof(p));
	assert(!mt6797_join_prepare_command(&t, 0x1c, 19, p, 16,
		output, sizeof(output), &cmd));
	puts("fixed mask validator and existing command boundaries PASS");
	return 0;
}
