/* SPDX-License-Identifier: GPL-2.0-only */
#include "test-compat.h"
#include <stdio.h>
#include <string.h>
#include "scan-wire.h"

static void request(void)
{
	unsigned char out[MT6797_PASSIVE_SCAN_BYTES], before[sizeof(out)];
	unsigned int channels[13];
	for (unsigned int n = 1; n <= 13; n++) {
		channels[n - 1] = n;
		assert(!mt6797_scan_request(1, channels, n, out));
		assert(out[0] == 1 && !out[1] && !out[2] && !out[5] && !out[7]);
		assert(!mt6797_normal_le16(out + 154));
		assert(!mt6797_normal_le16(out + 156));
		assert(out[158] == 4 && out[159] == n && !out[224] && !out[225]);
		for (unsigned int i = 0; i < n; i++)
			assert(out[160 + 2 * i] == 1 && out[161 + 2 * i] == i + 1);
		for (unsigned int i = 1; i < 154; i++) assert(!out[i]);
	}
	memcpy(before, out, sizeof(out));
	channels[12] = 1;
	assert(mt6797_scan_request(1, channels, 13, out) == -EINVAL);
	assert(!memcmp(before, out, sizeof(out)));
	channels[12] = 14;
	assert(mt6797_scan_request(1, channels, 13, out) == -EINVAL);
	assert(mt6797_scan_request(0, channels, 1, out) == -EINVAL);
	assert(mt6797_scan_request(256, channels, 1, out) == -EINVAL);
	assert(mt6797_scan_request(1, channels, 0, out) == -EINVAL);
	assert(mt6797_scan_request(1, channels, 14, out) == -EINVAL);
	assert(mt6797_scan_request(1, NULL, 1, out) == -EINVAL);
}
static void done(void)
{
	unsigned char packet[24] = {24, 0, 0, 0xe0, 0x0d, 0, 0, 0, 1};
	packet[12] = 13; packet[13] = 7;
	assert(!mt6797_scan_done(packet, sizeof(packet), 1, 13));
	assert(mt6797_scan_done(packet, sizeof(packet), 2, 13) == -EAGAIN);
	for (unsigned int n = 0; n < sizeof(packet); n++)
		assert(mt6797_scan_done(packet, n, 1, 13) == -EPROTO);
	for (unsigned int n = 0; n < sizeof(packet); n++) {
		unsigned char copy[24]; memcpy(copy, packet, sizeof(copy));
		if (n == 0 || n == 1 || n == 2 || n == 3 || n == 4 || n == 5 || n == 12 || n == 13) {
			copy[n] ^= 1;
			assert(mt6797_scan_done(copy, sizeof(copy), 1, 13) == -EPROTO);
		}
	}
}
static void frame(void)
{
	for (unsigned int groups = 0; groups < 16; groups++) {
		for (unsigned int pad = 0; pad <= 2; pad += 2) {
			unsigned char packet[128] = {0};
			struct mt6797_scan_frame result;
			unsigned int offset = 16, vector;
			if (groups & 8) offset += 16;
			if (groups & 1) offset += 16;
			if (groups & 2) offset += 8;
			vector = offset;
			if (groups & 4) offset += 24;
			unsigned int bytes = offset + pad + 36;
			packet[0] = bytes;
			packet[2] = 1; packet[3] = 0xe0 | groups << 1;
			packet[5] = 11; packet[6] = 24 | (pad ? 0x40 : 0);
			if (groups & 4) packet[vector + 9] = 100;
			packet[offset + pad] = 0x80;
			int ret = mt6797_scan_frame(packet, bytes, &result);
			if (groups & 4) {
				assert(!ret && result.offset == offset + pad && result.bytes == 36);
				assert(result.channel == 11 && result.rcpi == 100);
				for (unsigned int n = 0; n < bytes; n++) {
					unsigned char copy[128]; memcpy(copy, packet, sizeof(copy));
					copy[0] = n;
					assert(mt6797_scan_frame(copy, n, &result) != 0);
				}
				packet[6] |= 0x80;
				assert(mt6797_scan_frame(packet, bytes, &result) == -EOPNOTSUPP);
				packet[6] &= ~0x80;
				packet[vector + 9] = 255;
				assert(mt6797_scan_frame(packet, bytes, &result) == -EOPNOTSUPP);
				packet[vector + 9] = 100;
				packet[10] = 2;
				assert(mt6797_scan_frame(packet, bytes, &result) == -EOPNOTSUPP);
			} else assert(ret == -EOPNOTSUPP);
		}
	}
}
static void normal(void)
{
	unsigned char history[32] = {0}, out[256], payload[226] = {0};
	struct mt6797_normal_transaction t = {0};
	struct mt6797_hif_command command;
	assert(!mt6797_normal_admit(&t, 26, 26, history));
	t.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	assert(!mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_V2, 5,
		payload, sizeof(payload), out, sizeof(out), &command));
	assert(t.tc4_free == 24 && t.phase == MT6797_NORMAL_CONFIG_TX);
	assert(out[4] == 3 && out[6] == 1 && out[7] == 5 && out[0] == 234);
	assert(!mt6797_normal_submitted(&t, 0));
	assert(t.phase == MT6797_NORMAL_NVRAM_SUBMITTED && history[0] == (1 << 5));
	t.phase = MT6797_NORMAL_CAP_RECEIVED;
	assert(mt6797_normal_prepare_config(&t, MT6797_NORMAL_SCAN_V2, 6,
		payload, sizeof(payload), out, sizeof(out), &command) == -EIO);
}
int main(void)
{
	request(); done(); frame(); normal();
	puts("passive scan wire: pass; channel bounds, payload sequence, all RX groups and truncations");
	return 0;
}
