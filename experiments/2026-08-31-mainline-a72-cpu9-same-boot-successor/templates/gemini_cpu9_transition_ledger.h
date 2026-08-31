/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_GEMINI_CPU9_TRANSITION_LEDGER_H
#define _LINUX_GEMINI_CPU9_TRANSITION_LEDGER_H

#include <linux/errno.h>
#include <linux/gemini_transition_ledger.h>
#include <linux/types.h>

enum gemini_cpu9_transition_ledger_stage {
	GEMINI_CPU9_LEDGER_PRESTATE = 1,
	GEMINI_CPU9_LEDGER_CPU_ON,
	GEMINI_CPU9_LEDGER_ONLINE_WAIT,
	GEMINI_CPU9_LEDGER_IPI,
	GEMINI_CPU9_LEDGER_MEMBERSHIP,
};

enum gemini_cpu9_transition_ledger_terminal {
	GEMINI_CPU9_LEDGER_PRESTATE_FAILURE = 1,
	GEMINI_CPU9_LEDGER_CPU_ON_FAILURE,
	GEMINI_CPU9_LEDGER_ONLINE_WAIT_FAILURE,
	GEMINI_CPU9_LEDGER_IPI_FAILURE,
	GEMINI_CPU9_LEDGER_CPU9_ONLINE_PROOF,
};

#ifdef CONFIG_PSTORE_GEMINI_CPU9_TRANSITION_LEDGER
int gemini_cpu9_transition_ledger_begin(u64 cpu8_attempt_id,
					 u64 cpu9_attempt_id);
int gemini_cpu9_transition_ledger_checkpoint(u64 cpu9_attempt_id, u32 phase,
					      u32 stage, u32 terminal);
#else
static inline int gemini_cpu9_transition_ledger_begin(u64 cpu8_attempt_id,
						       u64 cpu9_attempt_id)
{
	return -EOPNOTSUPP;
}

static inline int gemini_cpu9_transition_ledger_checkpoint(u64 cpu9_attempt_id,
						    u32 phase, u32 stage,
						    u32 terminal)
{
	return -EOPNOTSUPP;
}
#endif

#endif /* _LINUX_GEMINI_CPU9_TRANSITION_LEDGER_H */
