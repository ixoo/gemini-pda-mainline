// SPDX-License-Identifier: GPL-2.0-only
#include "remap-fields.h"

int mt6797_remap_encode_common(unsigned long long base,
			       unsigned int enable, unsigned int *field)
{
	if (!field)
		return -EINVAL;
	*field = 0;
	if (enable > 1 || base > 0xffffffffULL - 0xfffffULL ||
	    base & 0xfffffULL)
		return -ERANGE;
	*field = (unsigned int)(base >> 20) | (enable * MT6797_REMAP_COMMON_ENABLE);
	return 0;
}

int mt6797_remap_encode_wlan(unsigned long long base, unsigned int *field)
{
	if (!field)
		return -EINVAL;
	*field = 0;
	if (base > 0xffffffffULL - 0xffffULL || base & 0xffffULL)
		return -ERANGE;
	*field = (unsigned int)base & MT6797_REMAP_WLAN_MASK;
	return 0;
}

static int mt6797_remap_replace(unsigned int current, unsigned int expected,
				unsigned int replacement, unsigned int mask,
				unsigned int *next)
{
	if (!next)
		return -EINVAL;
	*next = 0;
	if ((expected & ~mask) || (replacement & ~mask))
		return -EINVAL;
	if ((current & mask) != expected)
		return -EAGAIN;
	*next = (current & ~mask) | replacement;
	return 0;
}

int mt6797_remap_replace_common(unsigned int current,
				unsigned int expected, unsigned int replacement,
				unsigned int *next)
{
	return mt6797_remap_replace(current, expected, replacement,
				    MT6797_REMAP_COMMON_MASK, next);
}

int mt6797_remap_replace_wlan(unsigned int current,
			      unsigned int expected, unsigned int replacement,
			      unsigned int *next)
{
	return mt6797_remap_replace(current, expected, replacement,
				    MT6797_REMAP_WLAN_MASK, next);
}
