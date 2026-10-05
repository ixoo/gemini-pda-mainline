/* SPDX-License-Identifier: GPL-2.0-only */
/* Whole common-init step sequence against vendor vectors, synthetic patches. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "mt6797-wmt-common-init.h"

static unsigned char *patch_file(unsigned int sequence, unsigned int body)
{
	static const unsigned char address[2][4] = { { 0, 0, 0x0a, 0xf0 }, { 0, 0, 9, 0 } };
	unsigned char *file = calloc(1, body + 28);
	unsigned int i;

	assert(file);
	for (i = 0; i < 4; i++)
		file[24 + i] = address[sequence - 1][i];
	file[24] = 0x20 | sequence;
	for (i = 0; i < body; i++)
		file[28 + i] = (unsigned char)(i * 7 + sequence);
	return file;
}

int main(void)
{
	static const unsigned char dlm1[] = {
		0x01, 0x08, 0x10, 0x00, 0x01, 0x01, 0x00, 0x01, 0x60, 0x00, 0x10, 0x80,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x0f, 0x00, 0x00,
	};
	static const unsigned char clk_dis[] = {
		0x01, 0x08, 0x10, 0x00, 0x01, 0x01, 0x00, 0x01, 0x10, 0x11, 0x02, 0x81,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10,
	};
	static const unsigned char reset[] = { 0x01, 0x07, 0x01, 0x00, 0x04 };
	static const unsigned char coex[] = { 0x01, 0x10, 0x02, 0x00, 0x01, 0x01 };
	unsigned char *f1 = patch_file(1, 46444), *f2 = patch_file(2, 210876);
	unsigned char out[WMT_FULL_MAX_PAYLOAD], keep[WMT_FULL_MAX_PAYLOAD];
	struct wmt_rom_patch pair[2];
	struct wmt_init_step step, sentinel;
	unsigned int i, exchanges = 0, rails = 0, body = 0;

	assert(!wmt_rom_patch_parse(f1, 46444 + 28, 1, &pair[0]));
	assert(!wmt_rom_patch_parse(f2, 210876 + 28, 2, &pair[1]));
	assert(WMT_INIT_STEPS == 285 && WMT_INIT_CALIBRATION == 281);
	for (i = 0; i < WMT_INIT_STEPS; i++) {
		memset(out, 0xa5, sizeof(out));
		assert(!mt6797_wmt_init_step(pair, 1, i, out, sizeof(out), &step));
		if (step.kind == WMT_INIT_EXCHANGE) {
			exchanges++;
			assert(step.length >= 5 && step.length <= WMT_FULL_MAX_PAYLOAD);
			assert(out[0] == 1 && step.expected[0] == 2 && step.expected[1] == out[1]);
			/* Only calibration has a variable-size event (length 0). */
			if (i == WMT_INIT_CALIBRATION)
				assert(step.prefix == 2 && !step.expected_length);
			else
				assert(step.prefix && step.prefix <= step.expected_length &&
				       step.expected_length <= 8);
			if (out[1] == 1)
				body += step.length - 5;
		} else {
			rails++;
			assert(step.length == 0);
		}
	}
	assert(exchanges == 281 && rails == 4 && body == 46444 + 210876);
	/* Exact vendor vectors at fixed positions. */
	assert(!mt6797_wmt_init_step(pair, 1, 0, out, sizeof(out), &step));
	assert(step.length == sizeof(dlm1) && !memcmp(out, dlm1, sizeof(dlm1)));
	assert(step.prefix == 8 && step.expected[7] == 1);
	assert(!mt6797_wmt_init_step(pair, 1, 273, out, sizeof(out), &step));
	assert(step.length == sizeof(clk_dis) && !memcmp(out, clk_dis, sizeof(clk_dis)));
	assert(!mt6797_wmt_init_step(pair, 1, 7 + 49, out, sizeof(out), &step));
	assert(step.length == 5 && !memcmp(out, reset, 5));
	assert(!mt6797_wmt_init_step(pair, 1, 7 + 263, out, sizeof(out), &step));
	assert(step.length == 5 && !memcmp(out, reset, 5));
	assert(!mt6797_wmt_init_step(pair, 1, 275, out, sizeof(out), &step));
	assert(step.length == 73 && out[4] == 0x11);
	assert(!mt6797_wmt_init_step(pair, 1, 279, out, sizeof(out), &step) &&
	       step.kind == WMT_INIT_BT_RAIL_ON);
	assert(!mt6797_wmt_init_step(pair, 1, 280, out, sizeof(out), &step) &&
	       step.kind == WMT_INIT_WIFI_RAIL_ON);
	assert(!mt6797_wmt_init_step(pair, 1, 281, out, sizeof(out), &step));
	assert(step.length == 5 && out[1] == 0x14 && step.prefix == 2 &&
	       step.expected[0] == 0x02 && step.expected[1] == 0x14 &&
	       step.expected_length == 0);
	assert(!mt6797_wmt_init_step(pair, 1, 282, out, sizeof(out), &step) &&
	       step.kind == WMT_INIT_BT_RAIL_OFF);
	assert(!mt6797_wmt_init_step(pair, 1, 283, out, sizeof(out), &step) &&
	       step.kind == WMT_INIT_WIFI_RAIL_OFF);
	assert(!mt6797_wmt_init_step(pair, 1, 284, out, sizeof(out), &step));
	assert(step.length == sizeof(coex) && !memcmp(out, coex, sizeof(coex)));
	/* Refusals leave outputs unchanged. */
	memset(&sentinel, 0x5a, sizeof(sentinel));
	step = sentinel;
	memcpy(keep, out, sizeof(out));
	assert(mt6797_wmt_init_step(pair, 1, WMT_INIT_STEPS, out, sizeof(out), &step) == -1);
	assert(mt6797_wmt_init_step(pair, 256, 0, out, sizeof(out), &step) == -1);
	assert(mt6797_wmt_init_step(pair, 1, 0, out, 19, &step) == -1);
	assert(mt6797_wmt_init_step(pair, 1, 9, out, 100, &step) == -1);
	assert(!memcmp(&step, &sentinel, sizeof(step)) && !memcmp(out, keep, sizeof(out)));
	free(f1);
	free(f2);
	puts("wmt common-init sequence: 285 steps, 281 exchanges, vendor vectors pass");
	return 0;
}
