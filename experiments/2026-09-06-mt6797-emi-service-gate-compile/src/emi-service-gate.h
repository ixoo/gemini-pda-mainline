/* SPDX-License-Identifier: GPL-2.0-only */
/* One-attempt composition seam for the checked MT6797 EMI ABI. */
#ifndef GEMINI_MT6797_EMI_SERVICE_GATE_H
#define GEMINI_MT6797_EMI_SERVICE_GATE_H

#ifdef __KERNEL__
#include <linux/errno.h>
#include <linux/types.h>
#else
#include <assert.h>
#include <errno.h>
#include <stddef.h>
typedef unsigned long long u64;
#endif

#include "resource-layout.h"

static_assert(sizeof(u64) == 8, "EMI service gate requires 64-bit values");

/* The callback is deliberately an injected test/compile seam, not an SMC
 * implementation. Its context remains owned and stable by the caller.
 */
typedef u64 (*mt6797_emi_service_call)(void *context,
	unsigned int function_id, u64 start, u64 end,
	unsigned int region_permission);

struct mt6797_emi_service_backend {
	mt6797_emi_service_call call;
	void *context;
};

enum mt6797_emi_service_gate_state {
	MT6797_EMI_SERVICE_GATE_EMPTY,
	MT6797_EMI_SERVICE_GATE_READY,
	MT6797_EMI_SERVICE_GATE_ATTEMPTED,
	MT6797_EMI_SERVICE_GATE_COMPLETED,
	MT6797_EMI_SERVICE_GATE_FAULT_HELD,
};

struct mt6797_emi_service_gate {
	struct mt6797_resource_layout layout;
	struct mt6797_emi_service_backend backend;
	u64 expected_generation;
	enum mt6797_emi_service_gate_state state;
};

struct mt6797_emi_service_result {
	u64 generation;
	struct mt6797_emi_arguments arguments;
	u64 raw;
	int status;
};

int mt6797_emi_service_gate_init(struct mt6797_emi_service_gate *gate,
				 const struct mt6797_resource_layout *layout,
				 const struct mt6797_emi_service_backend *backend);

/* Caller-held external serialization is required: exactly-once applies are
 * guaranteed only for sequential or externally serialized calls; no lock-free
 * concurrency claim is made. backend.context is copied but not owned, so the
 * caller keeps its pointee alive and stable through apply. All non-identical
 * partial overlaps are caller preconditions; only exact aliases are detected.
 */
int mt6797_emi_service_gate_apply(struct mt6797_emi_service_gate *gate,
				  u64 expected_generation,
				  unsigned int permissions,
				  struct mt6797_emi_service_result *result);

#endif
