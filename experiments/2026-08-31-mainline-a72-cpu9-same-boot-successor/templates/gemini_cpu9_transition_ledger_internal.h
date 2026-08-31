/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __GEMINI_CPU9_TRANSITION_LEDGER_INTERNAL_H
#define __GEMINI_CPU9_TRANSITION_LEDGER_INTERNAL_H

#include "gemini_transition_ledger_internal.h"

struct gemini_cpu9_transition_ledger_owner {
	struct gemini_transition_ledger_owner ledger;
	bool attempted;
};

int cpu9_ledger_validate_cpu8(const struct gemini_transition_ledger_ops *ops,
			      void *context, u64 cpu8_attempt_id);
int cpu9_ledger_open(struct gemini_cpu9_transition_ledger_owner *owner,
		     const struct gemini_transition_ledger_ops *ops,
		     void *context, u64 cpu9_attempt_id);
int cpu9_ledger_owner_begin(struct gemini_cpu9_transition_ledger_owner *owner,
			    const struct gemini_transition_ledger_ops *cpu8_ops,
			    void *cpu8_context,
			    const struct gemini_transition_ledger_ops *cpu9_ops,
			    void *cpu9_context, u64 cpu8_attempt_id,
			    u64 cpu9_attempt_id);
int
cpu9_ledger_owner_checkpoint(struct gemini_cpu9_transition_ledger_owner *owner,
			     const struct gemini_transition_ledger_ops *ops, void *context,
	u64 cpu9_attempt_id, u32 phase, u32 stage, u32 terminal);

#endif /* __GEMINI_CPU9_TRANSITION_LEDGER_INTERNAL_H */
