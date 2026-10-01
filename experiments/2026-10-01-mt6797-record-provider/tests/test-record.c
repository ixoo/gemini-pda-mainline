/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic records only; no private calibration bytes or device access. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "record-prepare.h"

static void seal(uint8_t storage[MT6797_WIFI_STORAGE_BYTES])
{
	uint8_t check = 0;
	size_t i;

	for (i = 0; i < MT6797_WIFI_RECORD_BYTES; i++)
		check = i & 1 ? check ^ storage[i] : check + storage[i];
	storage[512] = 0xaa;
	storage[513] = check;
}

static void zero(const struct mt6797_record_commands *result)
{
	const uint8_t *p = (const uint8_t *)result;
	size_t i;

	for (i = 0; i < sizeof(*result); i++)
		assert(!p[i]);
}

static void fixture(uint8_t storage[MT6797_WIFI_STORAGE_BYTES])
{
	size_t i;

	memset(storage, 0, MT6797_WIFI_STORAGE_BYTES);
	storage[0] = storage[256] = 2; /* synthetic own versions */
	storage[2] = storage[258] = 0; /* synthetic peer versions */
	for (i = 0; i < 40; i++)
		storage[12 + i] = (uint8_t)(i + 1);
	for (i = 0; i < 11; i++)
		storage[112 + i] = (uint8_t)(0x40 + i);
	storage[62] = storage[123] = storage[196] = storage[198] =
		storage[262] = 1;
	storage[63] = 11; storage[64] = 12; storage[65] = 13;
	storage[124] = 0x5a; /* adjacent to the actual 5G AC validity flag */
	storage[156] = 0x6b; /* adjacent to the unsupported 2G AC flag */
	storage[199] = 21; storage[200] = 22; storage[201] = 23;
	seal(storage);
}

int main(void)
{
	uint8_t storage[MT6797_WIFI_STORAGE_BYTES];
	struct mt6797_record_commands result;
	static const uint8_t edge_5g[4] = {0, 11, 12, 13};
	static const uint8_t edge_2g[4] = {21, 22, 23, 0};
	static const size_t unsupported[] = {83, 104, 155, 266};
	size_t i;

	fixture(storage);
	assert(!mt6797_record_commands_from_storage(storage, sizeof(storage),
						    &result));
	assert(result.base_power && result.edge_5g && result.ac_5g &&
	       result.edge_2g);
	assert(!memcmp(result.base_power_bytes, storage + 12, 40));
	assert(!memcmp(result.edge_5g_bytes, edge_5g, 4));
	assert(result.ac_5g_bytes[0] == 2 &&
	       !memcmp(result.ac_5g_bytes + 1, storage + 112, 11));
	assert(!memcmp(result.edge_2g_bytes, edge_2g, 4));

	storage[123] = 0; /* the neighboring byte 124 stays nonzero */
	seal(storage);
	assert(!mt6797_record_commands_from_storage(storage, sizeof(storage),
						    &result));
	assert(!result.ac_5g);
	for (i = 0; i < sizeof(result.ac_5g_bytes); i++)
		assert(!result.ac_5g_bytes[i]);
	storage[123] = 1;
	for (i = 0; i < sizeof(unsupported) / sizeof(unsupported[0]); i++) {
		storage[unsupported[i]] = 1;
		seal(storage);
		memset(&result, 0xff, sizeof(result));
		assert(mt6797_record_commands_from_storage(storage,
							sizeof(storage),
							&result) == -EOPNOTSUPP);
		zero(&result);
		storage[unsupported[i]] = 0;
	}
	storage[0] = 1; /* selected legacy branch skips base command */
	seal(storage);
	assert(!mt6797_record_commands_from_storage(storage, sizeof(storage),
						    &result));
	assert(!result.base_power);
	storage[0] = 2;
	storage[262] = 0; /* 5G branch not taken */
	seal(storage);
	assert(!mt6797_record_commands_from_storage(storage, sizeof(storage),
						    &result));
	assert(!result.edge_5g && !result.ac_5g);
	storage[262] = 1;
	storage[2] = 1; storage[3] = 2; /* peer version 0x0201 */
	seal(storage);
	memset(&result, 0xff, sizeof(result));
	assert(mt6797_record_commands_from_storage(storage, sizeof(storage),
						     &result) == -EPROTONOSUPPORT);
	zero(&result);
	storage[2] = storage[3] = 0;
	seal(storage);
	storage[513] ^= 1;
	assert(mt6797_record_commands_from_storage(storage, sizeof(storage),
						     &result) == -EILSEQ);
	zero(&result);
	seal(storage);
	assert(mt6797_record_commands_from_storage(storage, 513, &result) ==
	       -EINVAL);
	zero(&result);
	assert(mt6797_record_commands_from_storage(NULL, 514, &result) ==
	       -EINVAL);
	zero(&result);
	puts("synthetic WIFI storage to conditional command payloads: pass");
	return 0;
}
