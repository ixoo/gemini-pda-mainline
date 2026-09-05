// SPDX-License-Identifier: GPL-2.0-only
#include <linux/crc32.h>
#include "mtke.h"

u32 mtke_crc32(const u8 *data, size_t size)
{
	return crc32_le(~0U, data, size) ^ ~0U;
}
