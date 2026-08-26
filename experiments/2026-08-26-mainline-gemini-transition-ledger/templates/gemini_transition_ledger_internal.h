/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __GEMINI_TRANSITION_LEDGER_INTERNAL_H
#define __GEMINI_TRANSITION_LEDGER_INTERNAL_H

#include <linux/types.h>

#define GEMINI_TRANSITION_LEDGER_PSTORE_SIGNATURE 0x43474244U
#define GEMINI_TRANSITION_LEDGER_MAGIC 0x4c543747U
#define GEMINI_TRANSITION_LEDGER_VERSION_WORD 0x00010009U
#define GEMINI_TRANSITION_LEDGER_HEADER_WORDS 3U
#define GEMINI_TRANSITION_LEDGER_COPY_WORDS 9U
#define GEMINI_TRANSITION_LEDGER_COPIES 2U
#define GEMINI_TRANSITION_LEDGER_INTEGRITY_WORD 8U
#define GEMINI_TRANSITION_LEDGER_PAYLOAD_BYTES \
	(GEMINI_TRANSITION_LEDGER_COPY_WORDS * \
	 GEMINI_TRANSITION_LEDGER_COPIES * sizeof(u32))
#define GEMINI_TRANSITION_LEDGER_SLOT_SIZE 0x1000U
#define GEMINI_TRANSITION_LEDGER_MAX_STAGE 9U
#define GEMINI_TRANSITION_LEDGER_MAX_TERMINAL 5U

struct gemini_transition_ledger_ops {
	u32 (*read)(void *context, unsigned int word);
	void (*write)(void *context, unsigned int word, u32 value);
	void (*barrier)(void *context);
};

struct gemini_transition_ledger_record {
	u64 attempt_id;
	u32 generation;
	u32 phase;
	u32 stage;
	u32 terminal;
};

struct gemini_transition_ledger_owner {
	u64 attempt_id;
	u32 next_generation;
	u32 newest_copy;
	u32 last_phase;
	u32 last_stage;
	bool active;
	bool sealed;
	bool failed;
	bool have_valid;
	bool have_checkpoint;
	bool header_committed;
	bool needs_signature;
};

int
gemini_transition_ledger_owner_begin(struct gemini_transition_ledger_owner *owner,
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 attempt_id);
int
gemini_transition_ledger_owner_checkpoint(struct gemini_transition_ledger_owner *owner,
	const struct gemini_transition_ledger_ops *ops, void *context,
	u64 attempt_id, u32 phase, u32 stage, u32 terminal);
bool
gemini_transition_ledger_read_latest(const struct gemini_transition_ledger_ops *ops,
	void *context,
	struct gemini_transition_ledger_record *record,
	u32 *copy_index);

#endif /* __GEMINI_TRANSITION_LEDGER_INTERNAL_H */
