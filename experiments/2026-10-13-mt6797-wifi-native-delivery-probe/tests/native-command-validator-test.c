// SPDX-License-Identifier: GPL-2.0-only
/* Exercise the REAL command validator/admission path mt6797_join_prepare_command
 * with the native SET_MONITOR CID 0xFC -- the path that refused ND1 at runtime
 * (first=-22 EINVAL). The encoder-only test could not catch this because it never
 * reached this validator. This is a PURE VALIDATOR/ENCODE fixture: it exercises the
 * admission decision and the 24-byte command the encoder emits; it does NOT drive the
 * HIF bus, the PIO transfer or the firmware. The runner compiles it twice: with
 * CONFIG_MT6797_NATIVE_DELIVERY_DIAG (0xFC admitted + field/length/ledger validated)
 * and without it (0xFC refused -- the normal-command boundary). Host, synthetic only. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "join-command-submit.h"

static void submitted(struct mt6797_normal_transaction *t, unsigned char *history)
{
	memset(t, 0, sizeof(*t));
	memset(history, 0, 32);
	assert(!mt6797_normal_admit(t, 4, 4, history));   /* COLD -> IDLE, tc4 4/4 */
	t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;          /* as join-hif-test.c does */
}

int main(void)
{
	struct mt6797_normal_transaction t;
	struct mt6797_hif_command command;
	unsigned char history[32], out[256], pay[16];

	memset(pay, 0, sizeof(pay));
	pay[0] = 1;             /* a minimal 16-byte payload for the CONFIG-off path */
	pay[2] = 40;
	submitted(&t, history);
	int base = mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command);
#ifdef CONFIG_MT6797_NATIVE_DELIVERY_DIAG
	assert(base == 0);
	/* Positive input built by the REAL encoder, so the caller/admission contract is
	 * exercised end to end up to (not including) the bus. */
	assert(mt6797_native_monitor_payload(true, 40, pay));
	submitted(&t, history);
	assert(mt6797_join_prepare_command(&t, 0xfc, 7, pay, 16, out, sizeof(out), &command) == 0);
	/* The emitted 24-byte normal command: length 24, CID 0xfc, is_set 1, sequence 7,
	 * then the exact payload; and the ledger/phase effects. */
	assert(out[0] == 24 && out[1] == 0 && out[3] == 0x80);
	assert(out[4] == 0xfc && out[5] == 0xa0 && out[6] == 1 && out[7] == 7);
	for (int i = 0; i < 16; i++)
		assert(out[8 + i] == pay[i]);
	assert(t.tc4_free == 3);                                  /* TC4 debit of 1 */
	assert(t.phase == MT6797_NORMAL_CONFIG_TX);
	assert(t.config_return_phase == MT6797_NORMAL_NVRAM_SUBMITTED);
	/* disable (ucEnable 0) via the encoder is equally valid */
	assert(mt6797_native_monitor_payload(false, 40, pay));
	submitted(&t, history);
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command) == 0);
	/* Length rejected before any field read: a short (and a long) buffer. */
	submitted(&t, history);
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 15, out, sizeof(out), &command) == -EINVAL);
	submitted(&t, history);
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 17, out, sizeof(out), &command) == -EINVAL);
	/* Bad exercised fields: enable>1, wrong channel, nonzero band, nonzero reserved. */
	submitted(&t, history); memset(pay, 0, 16); pay[0] = 2; pay[2] = 40;
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command) == -EINVAL);
	submitted(&t, history); memset(pay, 0, 16); pay[0] = 1; pay[2] = 36;
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command) == -EINVAL);
	submitted(&t, history); memset(pay, 0, 16); pay[0] = 1; pay[2] = 40; pay[1] = 1;
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command) == -EINVAL);
	submitted(&t, history); memset(pay, 0, 16); pay[0] = 1; pay[2] = 40; pay[9] = 1;
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command) == -EINVAL);
	/* Ledger/sequence guards apply to the new case too: a busy TC4 ledger refuses
	 * with -EBUSY, and sequence 0 is rejected -EINVAL. */
	assert(mt6797_native_monitor_payload(true, 40, pay));
	submitted(&t, history); t.tc4_free = 3;   /* debt outstanding */
	assert(mt6797_join_prepare_command(&t, 0xfc, 1, pay, 16, out, sizeof(out), &command) == -EBUSY);
	submitted(&t, history);
	assert(mt6797_join_prepare_command(&t, 0xfc, 0, pay, 16, out, sizeof(out), &command) == -EINVAL);
	puts("native-command-validator: PASS (CONFIG on: 0xfc admitted, 24B command + TC4/phase, "
	     "field/length/ledger refusals)");
#else
	/* Normal build: 0xFC is not a known command. ND1 itself ran with the diagnostic
	 * CONFIG present but this case ABSENT (the pre-fix regression below reproduces
	 * that); this branch only asserts the normal-build boundary is unchanged. */
	assert(base == -EINVAL);
	puts("native-command-validator: PASS (CONFIG off: 0xfc refused, boundary intact)");
#endif
	/* A normal command (0x1c, 16 bytes) is admitted in BOTH builds: the fix does not
	 * alter the existing allowlist. */
	submitted(&t, history);
	memset(pay, 0, sizeof(pay));
	assert(mt6797_join_prepare_command(&t, 0x1c, 1, pay, 16, out, sizeof(out), &command) == 0);
	return 0;
}
