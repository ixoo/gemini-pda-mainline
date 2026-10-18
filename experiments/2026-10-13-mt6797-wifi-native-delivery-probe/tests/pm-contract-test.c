/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "join-command-submit.h"

static size_t beacon(unsigned char *f, unsigned int interval, unsigned int period)
{
	memset(f, 0, 64); f[0] = 0x80; f[32] = interval; f[33] = interval >> 8;
	f[36] = 0; f[37] = 3; memcpy(f + 38, "lab", 3);
	f[41] = 5; f[42] = 4; f[43] = 0; f[44] = period;
	return 47;
}

static void metadata(void)
{
	unsigned char frame[96], copy[96], period, payload[12], saved[12];
	size_t n = beacon(frame, 100, 3);

	for (size_t cut = 0; cut <= n; cut++) {
		unsigned char *exact = malloc(cut ? cut : 1);
		assert(exact); memcpy(exact, frame, cut); period = 0xa5;
		int rc = mt6797_join_beacon_dtim(exact, cut, 100, &period);
		assert((rc == 0) == (cut == n)); assert(period == (cut == n ? 3 : 0xa5));
		assert(!memcmp(exact, frame, cut)); free(exact);
	}
	for (unsigned int dtim = 1; dtim <= 255; dtim++) {
		n = beacon(frame, 100, dtim); frame[43] = dtim - 1;
		assert(!mt6797_join_beacon_dtim(frame, n, 100, &period) && period == dtim);
		frame[43] = dtim; period = 0xa5;
		assert(mt6797_join_beacon_dtim(frame, n, 100, &period) && period == 0xa5);
	}
	n = beacon(frame, 100, 3); memcpy(copy, frame, sizeof(frame));
	period = 0xa5; memcpy(frame + n, frame + 41, 6);
	assert(mt6797_join_beacon_dtim(frame, n + 6, 100, &period) && period == 0xa5);
	memcpy(frame, copy, sizeof(frame)); frame[44] = 0;
	assert(mt6797_join_beacon_dtim(frame, n, 100, &period) && period == 0xa5);
	beacon(frame, 100, 3); frame[42] = 3;
	assert(mt6797_join_beacon_dtim(frame, n - 1, 100, &period));
	beacon(frame, 100, 3); frame[41] = 1;
	assert(mt6797_join_beacon_dtim(frame, n, 100, &period) == -ENOENT);
	beacon(frame, 100, 3);
	assert(mt6797_join_beacon_dtim(frame, n, 101, &period));
	frame[0] = 0x50; assert(mt6797_join_beacon_dtim(frame, n, 100, &period));
	assert(mt6797_join_beacon_dtim(NULL, n, 100, &period));
	assert(mt6797_join_beacon_dtim(frame, n, 100, NULL));
	memset(saved, 0xa5, sizeof(saved)); memcpy(payload, saved, sizeof(saved));
	for (unsigned int dtim = 0; dtim <= 256; dtim += 256) {
		assert(!mt6797_join_pm_connected_payload(dtim, 6, 100, payload));
		assert(!memcmp(payload, saved, 12));
	}
	assert(!mt6797_join_pm_connected_payload(3, 0, 100, payload));
	assert(!mt6797_join_pm_connected_payload(3, 2008, 100, payload));
	assert(!mt6797_join_pm_connected_payload(3, 6, 0, payload));
	assert(!mt6797_join_pm_connected_payload(3, 6, 65536, payload));
	assert(!memcmp(payload, saved, 12));
	assert(mt6797_join_pm_connected_payload(255, 2007, 65535, payload));
	assert(payload[0] == 0 && payload[1] == 255 && mt6797_join_le16(payload + 2) == 2007 && mt6797_join_le16(payload + 4) == 65535);
	for (unsigned int i = 6; i < 12; i++) assert(!payload[i]);
	assert(mt6797_join_pm_abort_payload(payload)); for (unsigned int i = 0; i < 4; i++) assert(!payload[i]);
}

static void ready(struct mt6797_normal_transaction *t, unsigned char history[32])
{
	*t = (struct mt6797_normal_transaction){0};
	assert(!mt6797_normal_admit(t, 4, 4, history));
	t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
}

static void ledger(void)
{
	struct mt6797_normal_transaction t;
	struct mt6797_hif_command cmd;
	unsigned char history[32] = {0}, payload[12], out[64], saved[64];
	struct mt6797_normal_release release;
	unsigned int words[8] = {0};

	assert(mt6797_join_pm_connected_payload(3, 6, 100, payload));
	ready(&t, history); memset(out, 0xa5, sizeof(out)); memcpy(saved, out, sizeof(out));
	for (unsigned int seq = 0; seq <= 256; seq += 256) {
		assert(mt6797_join_prepare_command(&t, 0x16, seq, payload, 12, out, sizeof(out), &cmd) == -EINVAL);
		assert(t.tc4_free == 4 && !memcmp(out, saved, sizeof(out)));
	}
	for (unsigned int bytes = 0; bytes <= 13; bytes++) {
		if (bytes == 12) continue;
		unsigned char *exact = malloc(bytes ? bytes : 1); assert(exact);
		memset(exact, 0, bytes);
		assert(mt6797_join_prepare_command(&t, 0x16, 19, exact, bytes, out, sizeof(out), &cmd) == -EINVAL);
		assert(t.tc4_free == 4 && !memcmp(out, saved, sizeof(out))); free(exact);
	}
	for (unsigned int field = 0; field < 12; field++) {
		if (field >= 1 && field <= 5) continue;
		unsigned char bad[12]; memcpy(bad, payload, 12); bad[field] = 1;
		assert(mt6797_join_prepare_command(&t, 0x16, 19, bad, 12, out, sizeof(out), &cmd) == -EINVAL);
		assert(t.tc4_free == 4 && !memcmp(out, saved, sizeof(out)));
	}
	assert(!mt6797_join_prepare_command(&t, 0x16, 19, payload, 12, out, sizeof(out), &cmd));
	assert(t.tc4_free == 3 && out[0] == 20 && out[4] == 0x16 && out[6] == 1 && out[7] == 19 && !memcmp(out + 8, payload, 12));
	assert(history[19 / 8] == (1U << (19 % 8)));
	assert(!mt6797_normal_submitted(&t, 0));
	assert(mt6797_join_prepare_command(&t, 0x17, 20, (unsigned char[4]){0}, 4, out, sizeof(out), &cmd) == -EBUSY);
	words[7] = (1U << 16) | 1; assert(!mt6797_normal_reconcile(&t, words, &release) && t.tc4_free == 4);
	assert(!mt6797_join_prepare_command(&t, 0x17, 20, (unsigned char[4]){0}, 4, out, sizeof(out), &cmd));
	assert(t.tc4_free == 3 && out[0] == 12 && out[4] == 0x17 && out[7] == 20);
	assert(mt6797_normal_submitted(&t, -EIO) < 0 && t.phase == MT6797_NORMAL_FAILED && t.tc4_free == 3);
}

#ifdef TEST_DEAUTH_RETIRE
static void deauth_debt(void)
{
	struct mt6797_normal_transaction t;
	struct mt6797_normal_release release;
	struct mt6797_hif_command cmd;
	unsigned char history[32] = {0}, out[64], saved[64], payload[4] = {0};
	unsigned int words[8] = {0};

	ready(&t, history); t.tc4_free--; t.tc4_pending_ffa = 1;
	assert(mt6797_join_cleanup_abort_ready(&t, 1));
	memset(out, 0xa5, sizeof(out)); memcpy(saved, out, sizeof(out));
	assert(mt6797_join_prepare_command(&t, 0x17, 21, payload, 4, out, sizeof(out), &cmd) == -EBUSY);
	assert(t.tc4_free == 3 && t.tc4_pending_ffa == 1 && !memcmp(out, saved, sizeof(out)));
	assert(mt6797_join_prepare_cleanup_abort(&t, 21, 0, out, sizeof(out), &cmd) == -EBUSY);
	assert(mt6797_join_prepare_cleanup_abort(&t, 21, 2, out, sizeof(out), &cmd) == -EBUSY);
	assert(!mt6797_join_prepare_cleanup_abort(&t, 21, 1, out, sizeof(out), &cmd));
	assert(t.tc4_free == 2 && t.tc4_pending_ffa == 1 && out[4] == 0x17 && out[7] == 21);
	assert(!mt6797_normal_submitted(&t, 0));
	/* One aggregate return cannot prove both outstanding buffers retired. */
	words[7] = 1U << 16;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.released_pages == 1 && t.tc4_free == 3);
	assert(mt6797_join_prepare_command(&t, 0x17, 22, payload, 4, out, sizeof(out), &cmd) == -EBUSY);
	words[7] = (1U << 16) | 1;
	assert(!mt6797_normal_reconcile(&t, words, &release) && t.tc4_free == 4);
	assert(!t.tc4_pending_cpu && !t.tc4_pending_ffa);
	assert(!mt6797_join_cleanup_abort_ready(&t, 1));
	assert(!mt6797_join_prepare_command(&t, 0x17, 22, payload, 4, out, sizeof(out), &cmd));
	assert(mt6797_normal_submitted(&t, -EIO) < 0 && t.tc4_free == 3);
	assert(!mt6797_join_cleanup_abort_ready(&t, 1));
	puts("deauth page ledger: PASS ordinary admission stays strict, bounded abort debit, partial/full returns, poison and no refund");
}

#endif

int main(void)
{
	metadata(); ledger();
#ifdef TEST_DEAUTH_RETIRE
	deauth_debt();
#endif
	puts("PM contract: PASS actual TIM bounds/unique/period/AID/interval, exact wire encoders and existing sequence/page-credit ownership; no firmware claim");
	return 0;
}
