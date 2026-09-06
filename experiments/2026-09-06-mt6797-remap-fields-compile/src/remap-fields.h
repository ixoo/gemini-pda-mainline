/* SPDX-License-Identifier: GPL-2.0-only */
/* Pure checked field arithmetic for the shared MT6797 remap register. */
#ifndef GEMINI_MT6797_REMAP_FIELDS_H
#define GEMINI_MT6797_REMAP_FIELDS_H

#ifdef __KERNEL__
#include <linux/build_bug.h>
#include <linux/errno.h>
#include <linux/types.h>
#else
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#endif

static_assert(sizeof(unsigned int) == 4,
	      "remap fields require 32-bit unsigned int");
static_assert(sizeof(int) == 4, "remap fields require 32-bit int");
static_assert(sizeof(unsigned long long) == 8,
	      "remap fields require 64-bit values");

#define MT6797_REMAP_COMMON_BASE_MASK 0x00000fffU
#define MT6797_REMAP_COMMON_ENABLE 0x00001000U
#define MT6797_REMAP_COMMON_MASK 0x00001fffU
#define MT6797_REMAP_WLAN_MASK 0xffff0000U

/* Encode a 1 MiB-aligned base and explicit enable state for bits 12:0.
 * The complete first MiB must remain in the 32-bit address space.
 */
int mt6797_remap_encode_common(unsigned long long base,
			       unsigned int enable, unsigned int *field);

/* Encode a 64 KiB-aligned base for the optional WLAN window in bits 31:16.
 * The complete first 64 KiB must remain in the 32-bit address space.
 */
int mt6797_remap_encode_wlan(unsigned long long base, unsigned int *field);

/* Replace only the owned field after proving the caller's expected state. */
int mt6797_remap_replace_common(unsigned int current,
				unsigned int expected, unsigned int replacement,
				unsigned int *next);
int mt6797_remap_replace_wlan(unsigned int current,
			      unsigned int expected, unsigned int replacement,
			      unsigned int *next);

#endif
