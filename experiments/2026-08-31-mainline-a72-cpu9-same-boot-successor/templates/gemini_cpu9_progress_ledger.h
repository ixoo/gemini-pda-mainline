/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_GEMINI_CPU9_PROGRESS_LEDGER_H
#define _LINUX_GEMINI_CPU9_PROGRESS_LEDGER_H

#include <linux/errno.h>
#include <linux/types.h>

enum gemini_cpu9_progress_stage {
	GEMINI_CPU9_PROGRESS_CPU8_PROOF = 1,
	GEMINI_CPU9_PROGRESS_READY_TOKEN,
	GEMINI_CPU9_PROGRESS_DERIVE,
	GEMINI_CPU9_PROGRESS_PUBLISH,
	GEMINI_CPU9_PROGRESS_PREPARE,
	GEMINI_CPU9_PROGRESS_ADD_CPU_DISPATCH,
	GEMINI_CPU9_PROGRESS_BINDER_ENTRY,
	GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_ENTER,
	GEMINI_CPU9_PROGRESS_LEDGER_BEGIN_RETURN,
	GEMINI_CPU9_PROGRESS_ADD_CPU_RETURN,
};

#ifdef CONFIG_PSTORE_GEMINI_CPU9_PROGRESS_LEDGER
int gemini_cpu9_progress_begin(u64 cpu8_attempt_id);
int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id, u32 stage);
#else
static inline int gemini_cpu9_progress_begin(u64 cpu8_attempt_id)
{
	return -EOPNOTSUPP;
}

static inline int gemini_cpu9_progress_checkpoint(u64 cpu8_attempt_id,
						   u32 stage)
{
	return -EOPNOTSUPP;
}
#endif

#endif /* _LINUX_GEMINI_CPU9_PROGRESS_LEDGER_H */
