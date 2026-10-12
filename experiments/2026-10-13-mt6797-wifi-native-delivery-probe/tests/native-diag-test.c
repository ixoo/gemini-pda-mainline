/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>

/* The driver includes net/mac80211.h for these; the unit test stubs them with
 * distinct bits so the no-bypass proof is exact. Values need not match the
 * kernel's; only their distinctness and the mask membership matter here. */
#define RX_FLAG_DECRYPTED      (1u << 0)
#define RX_FLAG_IV_STRIPPED    (1u << 1)
#define RX_FLAG_PN_VALIDATED   (1u << 2)
#define RX_FLAG_MMIC_STRIPPED  (1u << 3)
#define RX_FLAG_MIC_STRIPPED   (1u << 4)
#define RX_FLAG_ALLOW_SAME_PN  (1u << 5)
#define RX_FLAG_NO_SIGNAL_VAL  (1u << 6)
/* A decap/802.3 marker the diagnostic must never set on ordinary native RX. */
#define RX_FLAG_8023           (1u << 7)

#include "native-diag.h"
#include "join-commands.h"

int main(void)
{
	/* No-bypass proof: the ordinary native RX flag word sets NONE of the
	 * crypto bypass/strip flags, for both signal states, so mac80211 runs the
	 * full CCMP AEAD/MIC and the rx_pn replay check. */
	unsigned int mask = mt6797_native_diag_crypto_bypass_mask();
	assert(mask == (RX_FLAG_DECRYPTED | RX_FLAG_IV_STRIPPED | RX_FLAG_PN_VALIDATED |
			RX_FLAG_MMIC_STRIPPED | RX_FLAG_MIC_STRIPPED | RX_FLAG_ALLOW_SAME_PN));
	/* ALLOW_SAME_PN is in the mask and therefore never set (no same-PN accept). */
	assert(mask & RX_FLAG_ALLOW_SAME_PN);

	for (int sv = 0; sv <= 1; sv++) {
		unsigned int f = mt6797_native_diag_ordinary_flags(sv);
		assert((f & mask) == 0);          /* no crypto bypass/strip flag */
		assert((f & RX_FLAG_8023) == 0);  /* no 802.3/decap bypass */
		assert(f == (sv ? 0u : RX_FLAG_NO_SIGNAL_VAL));
	}

	/* Ceilings: under all ceilings CONTINUE; at each ceiling STOP. */
	struct mt6797_native_diag_budget b = {0, 0, 0, 0};
	assert(mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_CONTINUE);
	assert(mt6797_native_diag_budget_step(NULL) == MT6797_NATIVE_DIAG_STOP);
	struct mt6797_native_diag_budget wall = {MT6797_NATIVE_DIAG_WALL_MS, 0, 0, 0};
	struct mt6797_native_diag_budget rx = {0, MT6797_NATIVE_DIAG_RX_MAX, 0, 0};
	struct mt6797_native_diag_budget nat = {0, 0, MT6797_NATIVE_DIAG_NATIVE_MAX, 0};
	struct mt6797_native_diag_budget by = {0, 0, 0, MT6797_NATIVE_DIAG_BYTES_MAX};
	assert(mt6797_native_diag_budget_step(&wall) == MT6797_NATIVE_DIAG_STOP);
	assert(mt6797_native_diag_budget_step(&rx) == MT6797_NATIVE_DIAG_STOP);
	assert(mt6797_native_diag_budget_step(&nat) == MT6797_NATIVE_DIAG_STOP);
	assert(mt6797_native_diag_budget_step(&by) == MT6797_NATIVE_DIAG_STOP);
	/* The admitted ceiling values are exactly as root set them. */
	assert(MT6797_NATIVE_DIAG_WALL_MS == 10000u && MT6797_NATIVE_DIAG_RX_MAX == 512u &&
	       MT6797_NATIVE_DIAG_NATIVE_MAX == 64u && MT6797_NATIVE_DIAG_BYTES_MAX == (1u << 20));

	/* The 16-byte SET_MONITOR payload: enable/disable, band 0, primary 40, rest 0;
	 * only channel 40 admitted. */
	unsigned char cmd[MT6797_NATIVE_MONITOR_BYTES];
	assert(mt6797_native_monitor_payload(true, 40, cmd));
	assert(cmd[0] == 1 && cmd[1] == 0 && cmd[2] == 40);
	for (int i = 3; i < (int)MT6797_NATIVE_MONITOR_BYTES; i++)
		assert(cmd[i] == 0);
	assert(mt6797_native_monitor_payload(false, 40, cmd));
	assert(cmd[0] == 0 && cmd[1] == 0 && cmd[2] == 40);
	for (int i = 3; i < (int)MT6797_NATIVE_MONITOR_BYTES; i++)
		assert(cmd[i] == 0);
	assert(!mt6797_native_monitor_payload(true, 36, cmd));   /* only channel 40 */
	assert(!mt6797_native_monitor_payload(true, 40, NULL));

	/* Worker-state / ledger transitions: the asynchronous enable/disable state
	 * machine reconciled on the real credit/page ledger, never blocking. */
	{
		struct mt6797_native_diag_ctx c;
		struct mt6797_native_diag_budget z = {0, 0, 0, 0};
		struct mt6797_native_diag_budget full = {0, MT6797_NATIVE_DIAG_RX_MAX, 0, 0};

		/* Not armed, or not quiescent, stays IDLE (no pre-switch submission). */
		c = (struct mt6797_native_diag_ctx){MT6797_ND_IDLE, 0, 1, 1, 0, 0, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_IDLE);
		c = (struct mt6797_native_diag_ctx){MT6797_ND_IDLE, 1, 1, 0, 0, 0, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_IDLE);
		/* Armed + data phase + quiescent => submit enable, go ENABLE_PENDING. */
		c = (struct mt6797_native_diag_ctx){MT6797_ND_IDLE, 1, 1, 1, 0, 0, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_SUBMIT_ENABLE);
		assert(c.state == MT6797_ND_ENABLE_PENDING);
		/* Still owed (not quiescent): wait, no action, no early arm. */
		c.quiescent = 0;
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_ENABLE_PENDING);
		/* Enable retired (quiescent) => ACTIVE, still no action. */
		c.quiescent = 1;
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_ACTIVE);
		/* ACTIVE, a ceiling reached and quiescent => submit disable. */
		c.budget_stop = 1;
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_SUBMIT_DISABLE);
		assert(c.state == MT6797_ND_DISABLE_PENDING);
		/* Disable retired => CLOSED; cleanup now allowed. */
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_CLOSED);
		assert(mt6797_native_diag_cleanup_allowed(MT6797_ND_CLOSED));
		assert(mt6797_native_diag_cleanup_allowed(MT6797_ND_IDLE));
		assert(!mt6797_native_diag_cleanup_allowed(MT6797_ND_ENABLE_PENDING));
		assert(!mt6797_native_diag_cleanup_allowed(MT6797_ND_ACTIVE));
		assert(!mt6797_native_diag_cleanup_allowed(MT6797_ND_DISABLE_PENDING));
		/* Enable deadline passed => latch no-radio and close. */
		c = (struct mt6797_native_diag_ctx){MT6797_ND_ENABLE_PENDING, 1, 1, 0, 0, 1, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_LATCH_NORADIO && c.state == MT6797_ND_CLOSED);
		/* Disable deadline passed => latch no-radio and close. */
		c = (struct mt6797_native_diag_ctx){MT6797_ND_DISABLE_PENDING, 1, 1, 0, 0, 1, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_LATCH_NORADIO && c.state == MT6797_ND_CLOSED);
		/* Poison in any pending state closes without a radio command. */
		c = (struct mt6797_native_diag_ctx){MT6797_ND_ENABLE_PENDING, 1, 1, 1, 1, 0, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_CLOSED);
		/* PROOF: once first_error/closing is latched (poisoned), NO state yields a
		 * SUBMIT action — the diagnostic cannot slip a radio command past the
		 * existing fences; a pending state closes, and IDLE/ACTIVE never submit. */
		{
			int st;
			for (st = MT6797_ND_IDLE; st <= MT6797_ND_CLOSED; st++) {
				struct mt6797_native_diag_ctx q = {
					(enum mt6797_native_diag_state)st, 1, 1, 1, 1, 1, 1};
				enum mt6797_native_diag_action a = mt6797_native_diag_transition(&q);
				assert(a != MT6797_ND_ACT_SUBMIT_ENABLE &&
				       a != MT6797_ND_ACT_SUBMIT_DISABLE);
			}
		}
		/* IDLE poisoned: no enable. ACTIVE poisoned: no disable, closes. */
		c = (struct mt6797_native_diag_ctx){MT6797_ND_IDLE, 1, 1, 1, 1, 0, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_IDLE);
		c = (struct mt6797_native_diag_ctx){MT6797_ND_ACTIVE, 1, 1, 1, 1, 0, 1};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_CLOSED);
		c = (struct mt6797_native_diag_ctx){MT6797_ND_DISABLE_PENDING, 1, 1, 1, 1, 0, 0};
		assert(mt6797_native_diag_transition(&c) == MT6797_ND_ACT_NONE && c.state == MT6797_ND_CLOSED);
		/* Prospective admission: ACTIVE within caps admits; at a cap, no admit. */
		assert(mt6797_native_diag_admit(MT6797_ND_ACTIVE, &z));
		assert(!mt6797_native_diag_admit(MT6797_ND_ENABLE_PENDING, &z));  /* never deliver while pending */
		assert(!mt6797_native_diag_admit(MT6797_ND_ACTIVE, &full));       /* at RX cap: reject */
	}

	printf("native-diag: PASS (no crypto-bypass/802.3 flags, ALLOW_SAME_PN clear, ceilings 10s/512/64/1MiB, SET_MONITOR 16B band0/ch40; async worker state machine + ledger reconcile + cleanup gate + prospective admit)\n");
	return 0;
}
