/* SPDX-License-Identifier: GPL-2.0-only */
/* Original ABI validation arithmetic; provenance and limits in EMI_ABI.md. */
#ifndef GEMINI_EMI_ABI_H
#define GEMINI_EMI_ABI_H

#ifdef __KERNEL__
#include <linux/errno.h>
#include <linux/types.h>
#else
#include <errno.h>
#include <stddef.h>
#endif

_Static_assert(sizeof(unsigned int) == 4, "EMI ABI requires 32-bit unsigned int");
_Static_assert(sizeof(int) == 4, "EMI ABI requires 32-bit int");
_Static_assert(sizeof(unsigned long long) == 8, "EMI ABI requires 64-bit values");

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

/* Distinct output storage required. Zero output on every refusal.
 * Permissions are strictly low 24 bits; lock bit 26 and all other high bits
 * are refused rather than silently masked. Neither values nor region numbers
 * establish the caller's authority to set those fields.
 */
static inline int
mt6797_emi_prepare(const struct mt6797_emi_owner_range *owner,
	unsigned long long start, unsigned long long end,
	unsigned int permissions, struct mt6797_emi_arguments *arguments)
{
	unsigned long long translation, first, last;

	if (!arguments)
		return -EINVAL;
	*arguments = (struct mt6797_emi_arguments){0};
	if (!owner || owner->region < 2 || owner->region > 23 ||
	    permissions & ~0x00ffffffU)
		return -EINVAL;
	switch (owner->selector) {
	case MT6797_EMI_SELECTOR_BIT13_CLEAR:
		translation = 0x40000000ULL;
		break;
	case MT6797_EMI_SELECTOR_BIT13_SET:
		translation = 0;
		break;
	default:
		return -EINVAL;
	}
	/* Check before subtraction: neither reservation nor requested interval
	 * may rely on firmware underflow, upper-bit truncation or wrap.
	 */
	if (owner->start > owner->end || owner->start < translation ||
	    owner->end - translation > 0xffffffffULL || start > end ||
	    start < owner->start || end > owner->end ||
	    (start & 0xffffULL) || (end & 0xffffULL) != 0xffffULL)
		return -ERANGE;
	first = start - translation;
	last = end - translation;
	arguments->function_id = MT6797_EMI_SMC32_SET;
	arguments->start = start;
	arguments->end = end;
	arguments->region_permission = (owner->region << 27) | permissions;
	arguments->range_word = ((unsigned int)(first >> 16) << 16) |
		(unsigned int)(last >> 16);
	return 0;
}

/* Interpret low word without implementation-defined unsigned-to-signed cast.
 * Raw high bits are retained, not interpreted as a second success signal.
 * status is firmware status (including unknown values), not Linux errno.
 */
static inline struct mt6797_emi_result
mt6797_emi_decode_result(unsigned long long raw)
{
	unsigned int low = (unsigned int)(raw & 0xffffffffULL);
	struct mt6797_emi_result result = {.raw = raw};

	result.status = low <= 0x7fffffffU ? (int)low :
		-1 - (int)(0xffffffffU - low);
	return result;
}
#endif
