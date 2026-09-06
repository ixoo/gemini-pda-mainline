/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "emi-abi.h"

static void refused(const struct mt6797_emi_owner_range *owner,
	unsigned long long first, unsigned long long last, unsigned int policy)
{
	struct mt6797_emi_arguments args = {1, 2, 3, 4, 5};

	assert(mt6797_emi_prepare(owner, first, last, policy, &args) < 0);
	assert(!args.function_id && !args.start && !args.end &&
	       !args.region_permission && !args.range_word);
}

int main(void)
{
	struct mt6797_emi_owner_range owner = {
		.start = 0x80000000ULL, .end = 0x800fffffULL,
		.selector = MT6797_EMI_SELECTOR_BIT13_CLEAR, .region = 18,
	};
	struct mt6797_emi_arguments args;
	unsigned int selector, bit, region;
	unsigned long long offset;
	static const struct {
		unsigned long long raw;
		int status;
	} results[] = {
		{0, 0}, {0xffffffffULL, -1}, {0xfffffffeULL, -2},
		{0xfffffffdULL, -3}, {0xfffffffcULL, -4}, {0xfffffffbULL, -5},
		{1, 1}, {12345, 12345}, {0x7fffffffULL, INT_MAX},
		{0x80000000ULL, INT_MIN}, {0x80000001ULL, INT_MIN + 1},
		{0xffffffffffffffffULL, -1}, {0xdeadbeeffffffffdULL, -3},
		{0x1234567800000000ULL, 0}, {0x1234567800000001ULL, 1},
	};
	size_t i;

	assert(!mt6797_emi_prepare(&owner, 0x80000000, 0x8007ffff,
		0xb6da2d, &args));
	assert(args.function_id == 0x82000209U && args.start == 0x80000000ULL &&
	       args.end == 0x8007ffffULL && args.region_permission == 0x90b6da2dU &&
	       args.range_word == 0x40004007U);
	owner.selector = MT6797_EMI_SELECTOR_BIT13_SET;
	assert(!mt6797_emi_prepare(&owner, 0x80000000, 0x8007ffff, 0, &args));
	assert(args.range_word == 0x80008007U &&
	       args.region_permission == 0x90000000U);

	/* Every nonzero low-bit start offset and every non-ffff end is rejected,
	 * even though the retained handler would truncate these bits.
	 */
	for (offset = 1; offset <= 0xffff; offset++)
		refused(&owner, 0x80000000 + offset, 0x8007ffff, 0);
	for (offset = 0; offset < 0xffff; offset++)
		refused(&owner, 0x80000000, 0x80070000 + offset, 0);
	refused(&owner, 0x80000002, 0x80000001, 0);
	refused(&owner, 0x80080000, 0x8007ffff, 0);
	refused(&owner, 0x7fff0000, 0x8007ffff, 0);
	refused(&owner, 0x80000000, 0x8010ffff, 0);
	refused(&owner, 0, 0, 0);
	refused(&owner, 0, ULLONG_MAX, 0);
	refused(&owner, ULLONG_MAX, 0, 0);
	for (bit = 24; bit < 32; bit++)
		refused(&owner, 0x80000000, 0x8007ffff, 1U << bit);
	assert(!mt6797_emi_prepare(&owner, 0x80000000, 0x8007ffff,
		0xffffff, &args));
	assert(args.region_permission == 0x90ffffffU);
	for (region = 0; region < 32; region++) {
		owner.region = region;
		if (region >= 2 && region <= 23) {
			assert(!mt6797_emi_prepare(&owner, 0x80000000, 0x8000ffff,
				0, &args));
			assert(args.region_permission == region << 27);
		} else {
			refused(&owner, 0x80000000, 0x8000ffff, 0);
		}
	}
	owner.region = UINT_MAX;
	refused(&owner, 0x80000000, 0x8000ffff, 0);
	owner.region = 18;

	/* Full normalized domain edges, including an address above 4 GiB only
	 * when subtraction makes it non-aliasing.
	 */
	for (selector = 1; selector <= 2; selector++) {
		unsigned long long base = selector == 1 ? 0x40000000ULL : 0;

		owner.selector = (enum mt6797_emi_selector)selector;
		owner.start = base;
		owner.end = base + 0xffffffffULL;
		assert(!mt6797_emi_prepare(&owner, base, base + 0xffffffffULL,
			0, &args));
		assert(args.range_word == 0x0000ffffU);
		assert(!mt6797_emi_prepare(&owner, base + 0xffff0000ULL,
			base + 0xffffffffULL, 0, &args));
		assert(args.range_word == 0xffffffffU);
		refused(&owner, base + 0x100000000ULL,
			base + 0x10000ffffULL, 0);
		owner.end++;
		refused(&owner, base, base + 0xffff, 0);
		owner.end = ULLONG_MAX;
		refused(&owner, base, base + 0xffff, 0);
		if (base) {
			owner.start = base - 1;
			owner.end = base + 0xffff;
			refused(&owner, base, base + 0xffff, 0);
		}
	}
	owner.start = 0x80000000;
	owner.end = owner.start - 1;
	refused(&owner, 0x80000000, 0x8000ffff, 0);
	owner.end = 0x8000ffff;
	owner.selector = MT6797_EMI_SELECTOR_UNSET;
	refused(&owner, owner.start, owner.end, 0);
	owner.selector = (enum mt6797_emi_selector)-1;
	refused(&owner, owner.start, owner.end, 0);
	owner.selector = (enum mt6797_emi_selector)99;
	refused(&owner, owner.start, owner.end, 0);
	refused(NULL, 0x80000000, 0x8000ffff, 0);
	assert(mt6797_emi_prepare(&owner, 0, 0, 0, NULL) == -EINVAL);
	for (i = 0; i < sizeof(results) / sizeof(results[0]); i++) {
		struct mt6797_emi_result result =
			mt6797_emi_decode_result(results[i].raw);

		assert(result.raw == results[i].raw &&
		       result.status == results[i].status);
	}
	puts("emi_abi_alignment_131070_refusals_selector_bounds_status_cases=pass");
	return 0;
}
