/* SPDX-License-Identifier: GPL-2.0-only */
/* Pure composition of the initialized reserved-memory description. */
#ifndef GEMINI_MT6797_RESOURCE_LAYOUT_H
#define GEMINI_MT6797_RESOURCE_LAYOUT_H

#ifdef __KERNEL__
#include "emi-abi.h"
#include "image-binding.h"
#include "remap-fields.h"
#else
#include <assert.h>
#include <errno.h>
#include <stddef.h>
typedef unsigned long long u64;
#include "emi-abi.h"
#include "remap-fields.h"
struct mt6797_image_reserved_info {
	u64 generation;
	u64 start;
	u64 end;
	u64 wlan_start;
	u64 wlan_end;
	u64 wmt_start;
	u64 wmt_end;
};
#endif

static_assert(sizeof(u64) == 8, "resource layout requires 64-bit values");

/* Descriptive ranges only; no permission or access-policy fields are present. */
struct mt6797_resource_layout {
	u64 generation;
	u64 start;
	u64 end;
	u64 wlan_start;
	u64 wlan_end;
	u64 wmt_start;
	u64 wmt_end;
	unsigned int common_field;
	struct mt6797_emi_owner_range region18;
	struct mt6797_emi_owner_range region19;
};

/* Build the fixed first-MiB layout from an initialized, descriptive record. */
int mt6797_resource_layout_build(const struct mt6797_image_reserved_info *info,
				 enum mt6797_emi_selector selector,
				 struct mt6797_resource_layout *layout);

#endif
