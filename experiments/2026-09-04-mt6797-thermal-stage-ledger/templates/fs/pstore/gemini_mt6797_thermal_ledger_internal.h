/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __GEMINI_MT6797_THERMAL_LEDGER_INTERNAL_H
#define __GEMINI_MT6797_THERMAL_LEDGER_INTERNAL_H

#include <linux/types.h>

#define GEMINI_MT6797_THERMAL_LEDGER_PSTORE_SIGNATURE 0x43474244U
#define GEMINI_MT6797_THERMAL_LEDGER_MAGIC 0x4d485447U
#define GEMINI_MT6797_THERMAL_LEDGER_VERSION_WORD 0x0001000cU
#define GEMINI_MT6797_THERMAL_LEDGER_HEADER_WORDS 3U
#define GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS 12U
#define GEMINI_MT6797_THERMAL_LEDGER_COPIES 2U
#define GEMINI_MT6797_THERMAL_LEDGER_INTEGRITY_WORD 11U
#define GEMINI_MT6797_THERMAL_LEDGER_PAYLOAD_BYTES \
	(GEMINI_MT6797_THERMAL_LEDGER_COPY_WORDS * \
	 GEMINI_MT6797_THERMAL_LEDGER_COPIES * sizeof(u32))
#define GEMINI_MT6797_THERMAL_LEDGER_SLOT_SIZE 0x1000U
#define GEMINI_MT6797_THERMAL_LEDGER_MAX_RECORDS 96U
#define GEMINI_MT6797_THERMAL_LEDGER_MAX_BANK 5U
#define GEMINI_MT6797_THERMAL_LEDGER_ATTEMPT_ID 0x54484d4c00000001ULL

struct gemini_mt6797_thermal_ledger_ops {
	u32 (*read)(void *context, unsigned int word);
	void (*write)(void *context, unsigned int word, u32 value);
	void (*sync)(void *context);
};

struct gemini_mt6797_thermal_ledger_record {
	u64 attempt_id;
	u32 generation;
	u32 operation;
	u32 phase;
	u32 index;
	s32 result;
	u32 terminal;
};

struct gemini_mt6797_thermal_ledger_owner {
	u32 next_generation;
	u32 newest_copy;
	u32 records;
	bool active;
	bool sealed;
	bool failed;
	bool have_valid;
	bool header_committed;
	bool needs_signature;
};

int gemini_mt6797_thermal_ledger_owner_begin(
	struct gemini_mt6797_thermal_ledger_owner *owner,
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context);
int gemini_mt6797_thermal_ledger_owner_checkpoint(
	struct gemini_mt6797_thermal_ledger_owner *owner,
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context,
	u32 operation, u32 phase, u32 index, int result, u32 terminal);
bool gemini_mt6797_thermal_ledger_read_latest(
	const struct gemini_mt6797_thermal_ledger_ops *ops, void *context,
	struct gemini_mt6797_thermal_ledger_record *record, u32 *copy_index);

#endif /* __GEMINI_MT6797_THERMAL_LEDGER_INTERNAL_H */
