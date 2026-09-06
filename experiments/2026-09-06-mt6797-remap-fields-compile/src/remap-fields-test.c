/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include "remap-fields.h"

static void assert_common_refused(unsigned long long base,
				  unsigned int enable)
{
	unsigned int field = 0xa5a5a5a5U;

	assert(mt6797_remap_encode_common(base, enable, &field) < 0);
	assert(field == 0);
}

static void assert_wlan_refused(unsigned long long base)
{
	unsigned int field = 0xa5a5a5a5U;

	assert(mt6797_remap_encode_wlan(base, &field) < 0);
	assert(field == 0);
}

static void assert_replace_refused_common(unsigned int current,
					  unsigned int expected,
					  unsigned int replacement)
{
	unsigned int next = 0xa5a5a5a5U;

	assert(mt6797_remap_replace_common(current, expected, replacement,
					   &next) < 0);
	assert(next == 0);
}

static void assert_replace_refused_wlan(unsigned int current,
					unsigned int expected,
					unsigned int replacement)
{
	unsigned int next = 0xa5a5a5a5U;

	assert(mt6797_remap_replace_wlan(current, expected, replacement,
					 &next) < 0);
	assert(next == 0);
}

int main(void)
{
	unsigned int code, enable, field, next, neighbor;
	unsigned long long base;

	/* Both common enable states and both representable address edges. */
	assert(!mt6797_remap_encode_common(0, 0, &field) && field == 0);
	assert(!mt6797_remap_encode_common(0, 1, &field) &&
	       field == MT6797_REMAP_COMMON_ENABLE);
	assert(!mt6797_remap_encode_common(0xfff00000ULL, 0, &field) &&
	       field == MT6797_REMAP_COMMON_BASE_MASK);
	assert(!mt6797_remap_encode_common(0xfff00000ULL, 1, &field) &&
	       field == (MT6797_REMAP_COMMON_BASE_MASK |
			 MT6797_REMAP_COMMON_ENABLE));
	assert_common_refused(0x100000000ULL, 0);
	assert_common_refused(0xfff00001ULL, 0);
	assert_common_refused(0, 2);
	assert_common_refused(UINT_MAX, 0);
	for (base = 1; base < 0x100000ULL; base++)
		assert_common_refused(base, 0);
	assert_common_refused(0xfff00000ULL + 0x100000ULL, 0);
	for (code = 0; code <= MT6797_REMAP_COMMON_BASE_MASK; code++)
		for (enable = 0; enable <= 1; enable++)
			assert(!mt6797_remap_encode_common(
					(unsigned long long)code << 20, enable, &field) &&
					   field == (code | enable * MT6797_REMAP_COMMON_ENABLE));

	/* Both WLAN address edges, including complete-window overflow. */
	assert(!mt6797_remap_encode_wlan(0, &field) && field == 0);
	assert(!mt6797_remap_encode_wlan(0xffff0000ULL, &field) &&
	       field == MT6797_REMAP_WLAN_MASK);
	assert_wlan_refused(0x100000000ULL);
	assert_wlan_refused(0xffff0001ULL);
	assert_wlan_refused(UINT_MAX);
	for (base = 1; base < 0x10000ULL; base++)
		assert_wlan_refused(base);
	assert_wlan_refused(0xffff0000ULL + 0x10000ULL);
	for (code = 0; code <= 0xffffU; code++)
		assert(!mt6797_remap_encode_wlan((unsigned long long)code << 16,
						 &field) && field == code << 16);

	/* Null outputs refuse without attempting any arithmetic or write. */
	assert(mt6797_remap_encode_common(0, 0, NULL) == -EINVAL);
	assert(mt6797_remap_encode_wlan(0, NULL) == -EINVAL);
	assert(mt6797_remap_replace_common(0, 0, 0, NULL) == -EINVAL);
	assert(mt6797_remap_replace_wlan(0, 0, 0, NULL) == -EINVAL);

	/* Every common neighboring-bit pattern is preserved. */
	for (neighbor = 0; neighbor <= 0x7ffffU; neighbor++) {
		unsigned int current = (neighbor << 13) | 0x1000U;

		assert(!mt6797_remap_replace_common(current, 0x1000U, 0x1abcU,
						   &next));
		assert(next == ((neighbor << 13) | 0x1abcU));
	}
	/* Every WLAN neighboring-bit pattern is preserved. */
	for (neighbor = 0; neighbor <= 0xffffU; neighbor++) {
		unsigned int current = 0x12340000U | neighbor;

		assert(!mt6797_remap_replace_wlan(current, 0x12340000U,
						  0xabcd0000U,
						  &next));
		assert(next == (0xabcd0000U | neighbor));
	}

	/* Malformed owned fields and expected-state mismatches refuse and clear. */
	assert_replace_refused_common(0x12345000U, 0x2000U, 0);
	assert_replace_refused_common(0x12345000U, 0, 0x2000U);
	assert_replace_refused_common(0x12345000U, 0x1001U, 0);
	assert_replace_refused_wlan(0x12345678U, 1, 0);
	assert_replace_refused_wlan(0x12345678U, 0, 0x00000001U);
	assert_replace_refused_wlan(0x12345678U, 0xabcd0000U, 0);

	assert(!mt6797_remap_replace_common(0x80005000U, 0x1000U, 0x1abcU,
					   &next));
	assert(next == 0x80005abcu);
	assert(!mt6797_remap_replace_common(0x80000000U, 0, 1, &next));
	assert(next == 0x80000001U);
	assert(!mt6797_remap_replace_wlan(0x12345678U, 0x12340000U,
					   0xabcd0000U, &next));
	assert(next == 0xabcd5678U);

	puts("remap_fields_alignment_overflow_expected_state_neighbor_preservation=pass");
	return 0;
}
