// SPDX-License-Identifier: GPL-2.0-only
#include "emi-abi.h"

int mt6797_emi_prepare(const struct mt6797_emi_owner_range *owner,
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

struct mt6797_emi_result mt6797_emi_decode_result(unsigned long long raw)
{
	unsigned int low = (unsigned int)(raw & 0xffffffffULL);
	struct mt6797_emi_result result = {.raw = raw};

	result.status = low <= 0x7fffffffU ? (int)low :
		-1 - (int)(0xffffffffU - low);
	return result;
}
