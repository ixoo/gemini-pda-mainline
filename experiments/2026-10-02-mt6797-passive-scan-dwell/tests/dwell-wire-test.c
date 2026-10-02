/* SPDX-License-Identifier: GPL-2.0-only */
#include "test-compat.h"
#include <stdio.h>
#include <string.h>
#include "scan-wire.h"

int main(void)
{
	unsigned char out[MT6797_PASSIVE_SCAN_BYTES], before[sizeof(out)];
	unsigned int channels[2] = {40, 36};

	memset(out, 0xa5, sizeof(out));
	assert(!mt6797_scan_request(1, channels, 1, out));
	assert(out[0] == 1 && out[154] == 0xf4 && out[155] == 1);
	assert(mt6797_normal_le16(out + 154) == 500);
	assert(out[158] == 4 && out[159] == 1 && out[160] == 2 && out[161] == 40);
	for (unsigned int i = 1; i < sizeof(out); i++)
		if (i != 154 && i != 155 && (i < 158 || i > 161))
			assert(!out[i]);
	memcpy(before, out, sizeof(out));
	for (unsigned int count = 0; count <= MT6797_PASSIVE_SCAN_CHANNELS + 1; count++) {
		if (count == 1)
			continue;
		assert(mt6797_scan_request(1, channels, count, out) == -EINVAL);
		assert(!memcmp(before, out, sizeof(out)));
	}
	assert(mt6797_scan_request(0, channels, 1, out) == -EINVAL);
	assert(mt6797_scan_request(256, channels, 1, out) == -EINVAL);
	assert(mt6797_scan_request(1, NULL, 1, out) == -EINVAL);
	assert(mt6797_scan_request(1, channels, 1, NULL) == -EINVAL);
	channels[0] = 14;
	assert(mt6797_scan_request(1, channels, 1, out) == -EINVAL);
	assert(!memcmp(before, out, sizeof(out)));
	channels[0] = 40;
	assert(!mt6797_scan_request(255, channels, 1, out));
	assert(out[0] == 255 && mt6797_normal_le16(out + 154) == 500);
	puts("single_channel_dwell_wire=pass");
	return 0;
}
