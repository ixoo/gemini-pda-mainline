/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "join-submit.h"

/* The security-frame descriptor (pinned gen3 nicTxComposeSecurityFrameDesc
 * shape) and its preparation through the same TC4 ledger as management.
 */
static void ready(struct mt6797_normal_transaction *t, unsigned char *history, unsigned pages)
{
	*t = (struct mt6797_normal_transaction){0};
	assert(!mt6797_normal_admit(t, pages, pages, history));
	t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
}

int main(void)
{
	unsigned char e[1518] = {0}, sd[28], want[28] = {0}, hist[32], out[4096];
	struct mt6797_normal_transaction t;
	struct mt6797_hif_command c;
	unsigned pages;

	e[0] = 2; e[5] = 2; e[6] = 2; e[11] = 1; e[12] = 0x88; e[13] = 0x8e;
	want[0] = 28 + 113; want[2] = 20; want[3] = 0x88; want[4] = 1; want[5] = 0x90; want[7] = 4;
	want[10] = 15; want[11] = 0x80; want[12] = (3 << 11) & 255; want[13] = (3 << 11) >> 8;
	want[20] = 7; want[21] = 2; want[26] = (0x4b << 2) & 255; want[27] = (0x4b << 2) >> 8;
	assert(mt6797_join_tx_security_descriptor(e, 113, 1, 7, 500, 3, sd, &pages));
	assert(!memcmp(sd, want, 28) && pages == 2);
	assert(mt6797_join_tx_security_descriptor(e, 1518, 30, 127, 10000, 30, sd, &pages) && pages == 13);
	assert(!mt6797_join_tx_security_descriptor(e, 1519, 1, 7, 500, 3, sd, &pages));
	assert(!mt6797_join_tx_security_descriptor(e, 17, 1, 7, 500, 3, sd, &pages));
	e[12] = 0x08; assert(!mt6797_join_tx_security_descriptor(e, 113, 1, 7, 500, 3, sd, &pages)); e[12] = 0x88;
	e[0] = 1; assert(!mt6797_join_tx_security_descriptor(e, 113, 1, 7, 500, 3, sd, &pages)); e[0] = 2;
	e[6] = 1; assert(!mt6797_join_tx_security_descriptor(e, 113, 1, 7, 500, 3, sd, &pages)); e[6] = 2;
	assert(!mt6797_join_tx_security_descriptor(e, 113, 31, 7, 500, 3, sd, &pages));
	assert(!mt6797_join_tx_security_descriptor(e, 113, 1, 0, 500, 3, sd, &pages));
	assert(!mt6797_join_tx_security_descriptor(e, 113, 1, 7, 0, 3, sd, &pages));
	assert(!mt6797_join_tx_security_descriptor(e, 113, 1, 7, 500, 31, sd, &pages));
	assert(!mt6797_join_tx_security_descriptor(NULL, 113, 1, 7, 500, 3, sd, &pages));

	ready(&t, hist, 26);
	assert(!mt6797_join_prepare_security(&t, e, 113, 1, 9, 500, 3, out, sizeof(out), &c));
	assert(t.tc4_free == 24 && t.phase == MT6797_NORMAL_CONFIG_TX && out[5] == 0x90 && out[2] == 20);
	assert(!memcmp(out + 28, e, 113));
	t.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	assert(mt6797_join_prepare_security(&t, e, 113, 1, 10, 500, 3, out, sizeof(out), &c) == -EBUSY);
	ready(&t, hist, 1);
	assert(mt6797_join_prepare_security(&t, e, 113, 1, 9, 500, 3, out, sizeof(out), &c) == -ENOSPC);
	ready(&t, hist, 26);
	e[12] = 0;
	assert(mt6797_join_prepare_security(&t, e, 113, 1, 9, 500, 3, out, sizeof(out), &c) == -EINVAL);
	assert(t.tc4_free == 26);
	puts("join-security: PASS (descriptor shape, bounds and preparation under the TC4 ledger)");
	return 0;
}
