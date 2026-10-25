// SPDX-License-Identifier: GPL-2.0-only
/* Host fixture for 0274's budget step: under the 60-second window the CCMP
 * budget step stops at the checked-frame, total-frame and byte ceilings;
 * under the connected lifetime those ceilings are counts, never a stop (only
 * a missing budget stops). Compiled once with each define set.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
/* The mac80211 receive flags the header's bypass mask names (values as in the
 * native-diag fixture; only their presence matters here).
 */
#define RX_FLAG_DECRYPTED      (1u << 0)
#define RX_FLAG_IV_STRIPPED    (1u << 1)
#define RX_FLAG_PN_VALIDATED   (1u << 2)
#define RX_FLAG_MMIC_STRIPPED  (1u << 3)
#define RX_FLAG_MIC_STRIPPED   (1u << 4)
#define RX_FLAG_ALLOW_SAME_PN  (1u << 5)
#define RX_FLAG_NO_SIGNAL_VAL  (1u << 6)
#define RX_FLAG_8023           (1u << 7)
#include "native-diag.h"

int main(void)
{
	struct mt6797_native_diag_budget zero = {0, 0, 0, 0};
	struct mt6797_native_diag_budget checked = {0, 0, MT6797_CCMP_DIAG_CHECKED_MAX, 0};
	struct mt6797_native_diag_budget total = {0, MT6797_CCMP_DIAG_RX_MAX, 0, 0};
	struct mt6797_native_diag_budget bytes = {0, 0, 0, MT6797_CCMP_DIAG_BYTES_MAX};

	assert(mt6797_ccmp_diag_budget_step(NULL) == MT6797_NATIVE_DIAG_STOP);
	assert(mt6797_ccmp_diag_budget_step(&zero) == MT6797_NATIVE_DIAG_CONTINUE);
#ifdef CONFIG_MT6797_CCMP_CONNECTED_LIFETIME
	assert(mt6797_ccmp_diag_budget_step(&checked) == MT6797_NATIVE_DIAG_CONTINUE);
	assert(mt6797_ccmp_diag_budget_step(&total) == MT6797_NATIVE_DIAG_CONTINUE);
	assert(mt6797_ccmp_diag_budget_step(&bytes) == MT6797_NATIVE_DIAG_CONTINUE);
	printf("ccmp-budget-step-test: PASS (connected lifetime: ceilings are counts, not stops)\n");
#else
	assert(mt6797_ccmp_diag_budget_step(&checked) == MT6797_NATIVE_DIAG_STOP);
	assert(mt6797_ccmp_diag_budget_step(&total) == MT6797_NATIVE_DIAG_STOP);
	assert(mt6797_ccmp_diag_budget_step(&bytes) == MT6797_NATIVE_DIAG_STOP);
	printf("ccmp-budget-step-test: PASS (60-second window: ceilings stop)\n");
#endif
	return 0;
}
