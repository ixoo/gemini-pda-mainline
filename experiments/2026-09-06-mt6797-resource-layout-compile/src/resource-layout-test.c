/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "resource-layout.h"

static struct mt6797_image_reserved_info record(unsigned long long start,
						unsigned long long end,
						unsigned long long generation)
{
	return (struct mt6797_image_reserved_info){
		.generation = generation,
		.start = start,
		.end = end,
		.wlan_start = start,
		.wlan_end = start + 0x7ffffULL,
		.wmt_start = start + 0x80000ULL,
		.wmt_end = start + 0xfffffULL,
	};
}

static struct mt6797_resource_layout poisoned_layout(void)
{
	return (struct mt6797_resource_layout){
		.generation = 99,
		.start = 1,
		.end = 2,
		.wlan_start = 3,
		.wlan_end = 4,
		.wmt_start = 5,
		.wmt_end = 6,
		.common_field = 7,
		.region18 = {
			.start = 8,
			.end = 9,
			.selector = MT6797_EMI_SELECTOR_BIT13_CLEAR,
			.region = 18,
		},
		.region19 = {
			.start = 10,
			.end = 11,
			.selector = MT6797_EMI_SELECTOR_BIT13_SET,
			.region = 19,
		},
	};
}

static void assert_cleared(const struct mt6797_resource_layout *layout)
{
	assert(layout->generation == 0 && layout->start == 0 &&
	       layout->end == 0 && layout->wlan_start == 0 &&
	       layout->wlan_end == 0 && layout->wmt_start == 0 &&
	       layout->wmt_end == 0 && layout->common_field == 0 &&
	       layout->region18.start == 0 && layout->region18.end == 0 &&
	       layout->region18.selector == 0 && layout->region18.region == 0 &&
	       layout->region19.start == 0 && layout->region19.end == 0 &&
	       layout->region19.selector == 0 && layout->region19.region == 0);
}

static void expect_refused(struct mt6797_image_reserved_info *info,
					 enum mt6797_emi_selector selector)
{
	struct mt6797_resource_layout layout = poisoned_layout();

	assert(mt6797_resource_layout_build(info, selector, &layout) < 0);
	assert_cleared(&layout);
}

static void expect_success(unsigned long long start, unsigned long long end,
					 enum mt6797_emi_selector selector)
{
	struct mt6797_image_reserved_info info = record(start, end, 17);
	struct mt6797_resource_layout layout = {0};

	assert(!mt6797_resource_layout_build(&info, selector, &layout));
	assert(layout.generation == 17 && layout.start == start &&
	       layout.end == end && layout.wlan_start == start &&
	       layout.wlan_end == start + 0x7ffffULL &&
	       layout.wmt_start == start + 0x80000ULL &&
	       layout.wmt_end == start + 0xfffffULL);
	assert(layout.common_field == ((unsigned int)(start >> 20) | 0x1000U));
	assert(layout.region18.start == start &&
	       layout.region18.end == start + 0x7ffffULL &&
	       layout.region18.selector == selector && layout.region18.region == 18);
	assert(layout.region19.start == start + 0x80000ULL &&
	       layout.region19.end == start + 0xfffffULL &&
	       layout.region19.selector == selector && layout.region19.region == 19);
}

int main(void)
{
	struct mt6797_image_reserved_info info;
	struct mt6797_resource_layout layout;
	unsigned int field;
	unsigned int i;

	/* Minimum, larger-than-2 MiB, 1 MiB-only alignment, and address edges. */
	expect_success(0, 0xfffffULL, MT6797_EMI_SELECTOR_BIT13_SET);
	expect_success(0x40000000ULL, 0x402fffffULL,
		       MT6797_EMI_SELECTOR_BIT13_CLEAR);
	expect_success(0x80100000ULL, 0x803fffffULL,
		       MT6797_EMI_SELECTOR_BIT13_SET);
	expect_success(0xfff00000ULL, ULLONG_MAX,
		       MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);

	/* Nonzero generation, resource extent, and each reported subrange are required. */
	info.generation = 0;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x800ffffeULL, 17);
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.start = 0x80000001ULL;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.end = info.start + 0xffffeULL;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.end = info.start - 1;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.wlan_start++;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.wlan_end--;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.wmt_start++;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x80000000ULL, 0x802fffffULL, 17);
	info.wmt_end--;
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);

	/* Full-resource wrap and first-MiB remap overflow are distinct refusals. */
	info = record(ULLONG_MAX - 0x7ffffULL, ULLONG_MAX, 17);
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0xfff00001ULL, ULLONG_MAX, 17);
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	info = record(0x3ff00000ULL, 0x401fffffULL, 17);
	expect_refused(&info, MT6797_EMI_SELECTOR_BIT13_CLEAR);

	for (i = 0; i < 3; i++) {
		info = record(0x80000000ULL, 0x802fffffULL, 17);
		expect_refused(&info,
				      (enum mt6797_emi_selector[]){
					      MT6797_EMI_SELECTOR_UNSET,
					      (enum mt6797_emi_selector)3,
					      (enum mt6797_emi_selector)99,
				      }[i]);
	}

	/* Identical addresses are rejected before any input read and output clears. */
	layout = poisoned_layout();
	assert(mt6797_resource_layout_build(
			(const struct mt6797_image_reserved_info *)(const void *)&layout,
			MT6797_EMI_SELECTOR_BIT13_CLEAR, &layout) == -EINVAL);
	assert_cleared(&layout);
	expect_refused(NULL, MT6797_EMI_SELECTOR_BIT13_CLEAR);
	layout = poisoned_layout();
	assert(mt6797_resource_layout_build(NULL,
						MT6797_EMI_SELECTOR_BIT13_CLEAR, &layout) == -EINVAL);
	assert_cleared(&layout);
	assert(mt6797_resource_layout_build(&info,
						MT6797_EMI_SELECTOR_BIT13_CLEAR, NULL) == -EINVAL);

	/* The constructor does not expose or manufacture a permission policy. */
	assert(!mt6797_remap_encode_common(0x80000000ULL, 1, &field));
	assert(field == 0x1800U);
	puts("resource_layout_ranges_generation_selector_overflow_alias=pass");
	return 0;
}
