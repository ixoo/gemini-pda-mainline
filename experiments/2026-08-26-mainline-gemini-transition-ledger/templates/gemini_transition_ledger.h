/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_GEMINI_TRANSITION_LEDGER_H
#define _LINUX_GEMINI_TRANSITION_LEDGER_H

#include <linux/errno.h>
#include <linux/types.h>

enum gemini_transition_ledger_phase {
	GEMINI_TRANSITION_LEDGER_BEFORE = 1,
	GEMINI_TRANSITION_LEDGER_AFTER,
	GEMINI_TRANSITION_LEDGER_TERMINAL,
};

#ifdef CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER
int gemini_transition_ledger_begin(u64 attempt_id);
int gemini_transition_ledger_checkpoint(u64 attempt_id, u32 phase,
					u32 stage, u32 terminal);
#else
static inline int gemini_transition_ledger_begin(u64 attempt_id)
{
	return -EOPNOTSUPP;
}

static inline int gemini_transition_ledger_checkpoint(u64 attempt_id, u32 phase,
					      u32 stage, u32 terminal)
{
	return -EOPNOTSUPP;
}
#endif

#endif /* _LINUX_GEMINI_TRANSITION_LEDGER_H */
