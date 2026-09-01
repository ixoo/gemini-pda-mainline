/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __GEMINI_CPU9_PROGRESS_LEDGER_INTERNAL_H
#define __GEMINI_CPU9_PROGRESS_LEDGER_INTERNAL_H

#include "gemini_transition_ledger_internal.h"

struct gemini_cpu9_progress_owner {
	struct gemini_transition_ledger_owner ledger;
	bool attempted;
};

int cpu9_progress_owner_begin(
	struct gemini_cpu9_progress_owner *owner,
	const struct gemini_transition_ledger_ops *cpu8_ops,
	void *cpu8_context,
	const struct gemini_transition_ledger_ops *progress_ops,
	void *progress_context, u64 cpu8_attempt_id);
int cpu9_progress_owner_checkpoint(
	struct gemini_cpu9_progress_owner *owner,
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu8_attempt_id, u32 stage);

#endif /* __GEMINI_CPU9_PROGRESS_LEDGER_INTERNAL_H */
