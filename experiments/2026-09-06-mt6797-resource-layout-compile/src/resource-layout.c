// SPDX-License-Identifier: GPL-2.0-only
#include "resource-layout.h"

int mt6797_resource_layout_build(const struct mt6797_image_reserved_info *info,
				 enum mt6797_emi_selector selector,
				 struct mt6797_resource_layout *layout)
{
	unsigned int common_field;
	int error;

	if (!layout)
		return -EINVAL;
	if ((const void *)info == (const void *)layout) {
		*layout = (struct mt6797_resource_layout){0};
		return -EINVAL;
	}
	*layout = (struct mt6797_resource_layout){0};
	if (!info)
		return -EINVAL;
	if (info->generation == 0 || info->start > info->end ||
	    info->start > 0xffffffffffffffffULL - 0xfffffULL ||
	    info->end - info->start < 0xfffffULL)
		return -ERANGE;
	if (info->wlan_start != info->start ||
	    info->wlan_end != info->start + 0x7ffffULL ||
	    info->wmt_start != info->start + 0x80000ULL ||
	    info->wmt_end != info->start + 0xfffffULL)
		return -ERANGE;
	switch (selector) {
	case MT6797_EMI_SELECTOR_BIT13_CLEAR:
	case MT6797_EMI_SELECTOR_BIT13_SET:
		break;
	default:
		return -EINVAL;
	}
	if (selector == MT6797_EMI_SELECTOR_BIT13_CLEAR &&
	    info->start < 0x40000000ULL)
		return -ERANGE;
	error = mt6797_remap_encode_common(info->start, 1, &common_field);
	if (error)
		return error;
	*layout = (struct mt6797_resource_layout){
		.generation = info->generation,
		.start = info->start,
		.end = info->end,
		.wlan_start = info->wlan_start,
		.wlan_end = info->wlan_end,
		.wmt_start = info->wmt_start,
		.wmt_end = info->wmt_end,
		.common_field = common_field,
		.region18 = {
			.start = info->wlan_start,
			.end = info->wlan_end,
			.selector = selector,
			.region = 18,
		},
		.region19 = {
			.start = info->wmt_start,
			.end = info->wmt_end,
			.selector = selector,
			.region = 19,
		},
	};
	return 0;
}
