/* SPDX-License-Identifier: GPL-2.0-only */
/* Original ABI validation arithmetic; provenance and limits in EMI_ABI.md. */
#ifndef GEMINI_EMI_ABI_H
#define GEMINI_EMI_ABI_H

#ifdef __KERNEL__
#include <linux/build_bug.h>
#include <linux/errno.h>
#include <linux/types.h>
#else
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#endif

static_assert(sizeof(unsigned int) == 4, "EMI ABI requires 32-bit unsigned int");
static_assert(sizeof(int) == 4, "EMI ABI requires 32-bit int");
static_assert(sizeof(unsigned long long) == 8, "EMI ABI requires 64-bit values");

#define MT6797_EMI_SMC32_SET 0x82000209U

/* Zero-initialized or unknown selector context is deliberately inadmissible. */
enum mt6797_emi_selector {
	MT6797_EMI_SELECTOR_UNSET,
	MT6797_EMI_SELECTOR_BIT13_CLEAR,
	MT6797_EMI_SELECTOR_BIT13_SET,
};

/* Facts supplied by an existing exclusive owner, not an acquired lease.
 * Inclusive reservation and region ownership must remain valid through the
 * eventual call. This helper does not read/lock the global selector or MMIO.
 */
struct mt6797_emi_owner_range {
	unsigned long long start;
	unsigned long long end;
	enum mt6797_emi_selector selector;
	unsigned int region;
};

struct mt6797_emi_arguments {
	unsigned int function_id;
	unsigned long long start;
	unsigned long long end;
	unsigned int region_permission;
	/* Expected encoded register word for review; never written by this helper. */
	unsigned int range_word;
};

struct mt6797_emi_result {
	unsigned long long raw;
	int status;
};

/* Distinct output storage is a caller precondition; zero output on every
 * refusal. The helper does not attempt to identify storage aliases.
 * Permissions are strictly low 24 bits; lock bit 26 and all other high bits
 * are refused rather than silently masked. Neither values nor region numbers
 * establish the caller's authority to set those fields.
 */
int mt6797_emi_prepare(const struct mt6797_emi_owner_range *owner,
		       unsigned long long start, unsigned long long end,
		       unsigned int permissions, struct mt6797_emi_arguments *arguments);

/* Interpret the low word without implementation-defined unsigned-to-signed
 * conversion. Raw high bits are retained, not interpreted as success.
 */
struct mt6797_emi_result mt6797_emi_decode_result(unsigned long long raw);

#endif
