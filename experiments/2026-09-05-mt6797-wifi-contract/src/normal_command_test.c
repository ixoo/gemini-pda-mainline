/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "normal_command.h"
#include "hif_pio.h"

struct fake_normal {
	unsigned int calls, fail, reads;
	unsigned char reply[128];
};

static int write_word(void *context, unsigned int offset, unsigned int value)
{
	struct fake_normal *f = context;
	unsigned int n = f->calls, expected_offset = 0x1000, expected;

	if (!n) { expected_offset = 0; expected = 0x9000687c; }
	else if (n == 1) expected = 0x8000007c;
	else if (n == 2) expected = 0x2900a080;
	else if (n < 32) expected = 0;
	else if (n == 32) { expected_offset = 0; expected = 0x1000a880; }
	else if (n == 65) { expected_offset = 0; expected = 0x98006802; }
	else if (n == 66) expected = 0x80000208;
	else if (n == 67) expected = 0x2a01a048;
	else if (n < 196) expected = 0x5a5a5a5a;
	else { assert(n < 322); expected = 0; }
	assert(offset == expected_offset && value == expected);
	return ++f->calls == f->fail ? -EIO : 0;
}

static int read_word(void *context, unsigned int offset, unsigned int *value)
{
	struct fake_normal *f = context;
	unsigned int i = f->reads * 4;

	assert(offset == 0x1000 && f->calls >= 33 && f->calls < 65 && i < 128);
	*value = (unsigned int)f->reply[i] | ((unsigned int)f->reply[i + 1] << 8) |
		((unsigned int)f->reply[i + 2] << 16) | ((unsigned int)f->reply[i + 3] << 24);
	f->reads++;
	return ++f->calls == f->fail ? -EIO : 0;
}

static void capability_packet(unsigned char *p)
{
	memset(p, 0, 128);
	p[0] = 124; p[3] = 0xe0; p[4] = 1; p[5] = 41;
	p[8] = 0x34; p[9] = 0x12; p[10] = 2; p[11] = 3;
	p[12] = 4; p[13] = 5; p[14] = 7; p[15] = 9;
	p[26] = 0xfe; p[27] = 0xff;
}

static void waiting(struct mt6797_normal_transaction *t, unsigned char *history)
{
	unsigned char buffer[124];
	struct mt6797_hif_command command;

	*t = (struct mt6797_normal_transaction){0};
	memset(history, 0, 32);
	assert(!mt6797_normal_admit(t, 26, 26, history));
	assert(!mt6797_normal_prepare(t, MT6797_NORMAL_CAPABILITY, 41,
		NULL, 0, buffer, sizeof(buffer), &command));
	assert(!mt6797_normal_submitted(t, 0));
}

int main(void)
{
	unsigned char history[32], frame[1024], payload[512], packet[128];
	struct mt6797_normal_transaction t;
	struct mt6797_normal_capability result;
	struct mt6797_hif_command command;
	unsigned int fail, length, index, value;

	memset(payload, 0x5a, sizeof(payload));
	for (fail = 0; fail <= 322; fail++) {
		struct fake_normal fake = {.fail = fail};
		struct mt6797_hif_pio_io io = {&fake, write_word, read_word};
		struct mt6797_hif_pio_result transfer;
		int error;

		capability_packet(fake.reply);
		memset(history, 0, sizeof(history));
		history[2] = 8; /* Existing INIT sequence 19 remains owned/used. */
		t = (struct mt6797_normal_transaction){0};
		assert(!mt6797_normal_admit(&t, 26, 26, history));
		assert(!mt6797_normal_prepare(&t, MT6797_NORMAL_CAPABILITY, 41,
			NULL, 0, frame, sizeof(frame), &command));
		assert(t.tc4_free == 25 && history[2] == 8 && (history[5] & 2));
		error = mt6797_hif_pio_transfer(&io, 0x34, MT6797_HIF_WRITE,
			frame, 124, sizeof(frame), &transfer);
		error = mt6797_normal_submitted(&t, error);
		if (!error) {
			assert(mt6797_normal_reply_span(&t, 0, 128, &command) == -EAGAIN);
			assert(!mt6797_normal_reply_span(&t, 124, 128, &command));
			assert(command.word == 0x1000a880 && command.transfer_bytes == 128);
			error = mt6797_hif_pio_transfer(&io, 0x54, MT6797_HIF_READ,
				packet, 128, sizeof(packet), &transfer);
			if (error) mt6797_normal_abort(&t);
			else error = mt6797_normal_accept_capability(&t, packet, 124, &result);
		}
		if (!error) {
			assert(result.product == 0x1234 && result.firmware_own == 0x302 &&
			       result.firmware_peer == 0x504 && result.hw_5g_disabled == 7 &&
			       result.eeprom_used == 9 && result.rf_cal_fail == 0xfe &&
			       result.bb_cal_fail == 0xff); /* Parsed, not calibration success. */
			assert(!mt6797_normal_prepare(&t, MT6797_NORMAL_NVRAM, 42,
				payload, sizeof(payload), frame, sizeof(frame), &command));
			assert(command.word == 0x98006802 && command.transfer_bytes == 1024);
			assert(t.tc4_free == 20 && (history[5] & 6) == 6);
			assert(!memcmp(frame + 8, payload, 512));
			error = mt6797_hif_pio_transfer(&io, 0x34, MT6797_HIF_WRITE,
				frame, 520, sizeof(frame), &transfer);
			error = mt6797_normal_submitted(&t, error);
		}
		assert(t.tc4_free == (fail && fail <= 65 ? 25U : 20U));
		if (fail) {
			assert(error && fake.calls == fail && t.phase == MT6797_NORMAL_FAILED);
			assert(mt6797_normal_submitted(&t, 0) < 0 && fake.calls == fail);
		} else {
			assert(!error && fake.calls == 322 && t.phase == MT6797_NORMAL_NVRAM_SUBMITTED);
			assert(mt6797_normal_reply_span(&t, 124, 128, &command) < 0);
			assert(t.tc4_free == 20); /* No invented NVRAM ACK/refund. */
		}
	}
	/* Exact reply framing and expected sequence, beyond the weak vendor checks. */
	for (length = 0; length <= 129; length++) {
		waiting(&t, history); capability_packet(packet);
		if (length == 124) assert(!mt6797_normal_accept_capability(&t, packet, length, &result));
		else {
			result.product = 1;
			assert(mt6797_normal_accept_capability(&t, packet, length, &result) < 0);
			assert(!result.product && t.phase == MT6797_NORMAL_FAILED);
		}
	}
	for (index = 0; index < 6; index++) {
		for (value = 0; value < 256; value++) {
			unsigned char original;

			waiting(&t, history); capability_packet(packet);
			original = packet[index]; packet[index] = (unsigned char)value;
			assert((mt6797_normal_accept_capability(&t, packet, 124, &result) == 0) ==
			       (original == value));
		}
	}
	/* Reserved/MAC/date/feature bytes have no effect on selected output fields. */
	for (index = 6; index < 124; index++) {
		if ((index >= 8 && index <= 15) || index == 26 || index == 27)
			continue;
		waiting(&t, history); capability_packet(packet);
		packet[index] = 0xa5;
		assert(!mt6797_normal_accept_capability(&t, packet, 124, &result));
		assert(result.product == 0x1234 && result.rf_cal_fail == 0xfe &&
		       result.bb_cal_fail == 0xff);
	}
	for (index = 0; index < sizeof(payload); index++)
		assert(payload[index] == 0x5a);
	for (length = 0; length <= 0xffff; length++) {
		waiting(&t, history);
		if (!length) assert(mt6797_normal_reply_span(&t, length, 128, &command) == -EAGAIN);
		else if (length == 124) assert(!mt6797_normal_reply_span(&t, length, 128, &command));
		else assert(mt6797_normal_reply_span(&t, length, 128, &command) < 0 && !command.word);
	}
	for (length = 0; length < 128; length++) {
		waiting(&t, history);
		assert(mt6797_normal_reply_span(&t, 124, length, &command) < 0);
	}
	waiting(&t, history); capability_packet(packet);
	assert(!mt6797_normal_accept_capability(&t, packet, 124, &result));
	assert(mt6797_normal_prepare(&t, MT6797_NORMAL_NVRAM, 41,
		payload, 512, frame, sizeof(frame), &command) < 0 && t.tc4_free == 25);
	waiting(&t, history);
	assert(mt6797_normal_prepare(&t, MT6797_NORMAL_NVRAM, 42,
		payload, 512, frame, sizeof(frame), &command) < 0); /* Before capability. */
	t = (struct mt6797_normal_transaction){0}; memset(history, 0, 32); history[2] = 8;
	assert(!mt6797_normal_admit(&t, 26, 26, history));
	assert(mt6797_normal_prepare(&t, MT6797_NORMAL_CAPABILITY, 19,
		NULL, 0, frame, sizeof(frame), &command) < 0 && t.tc4_free == 26);
	waiting(&t, history); capability_packet(packet);
	assert(!mt6797_normal_accept_capability(&t, packet, 124, &result));
	t.tc4_free = 4; memset(frame, 0x7a, sizeof(frame));
	assert(mt6797_normal_prepare(&t, MT6797_NORMAL_NVRAM, 42,
		payload, 512, frame, sizeof(frame), &command) == -ENOSPC);
	assert(t.tc4_free == 4 && !(history[5] & 4) && frame[0] == 0x7a);
	for (length = 0; length <= 514; length++) {
		if (length == 512) continue;
		assert(mt6797_normal_prepare(&t, MT6797_NORMAL_NVRAM, 42,
			payload, length, frame, sizeof(frame), &command) == -EINVAL);
	}
	t.tc4_free = 25;
	assert(mt6797_normal_prepare(&t, MT6797_NORMAL_NVRAM, 42,
		payload, 512, frame, 1023, &command) < 0 && t.tc4_free == 25);
	assert(mt6797_normal_admit(&t, 26, 26, history) < 0 && t.phase == MT6797_NORMAL_FAILED);
	t = (struct mt6797_normal_transaction){0};
	assert(mt6797_normal_admit(&t, 0, 0, history) < 0);
	assert(mt6797_normal_admit(&t, 26, 27, history) < 0);
	assert(mt6797_normal_admit(&t, 65536, 0, history) < 0);
	assert(mt6797_normal_admit(&t, 26, 26, NULL) < 0);
	assert(mt6797_normal_accept_capability(NULL, packet, 124, &result) < 0);
	waiting(&t, history);
	assert(mt6797_normal_accept_capability(&t, NULL, 124, &result) < 0);
	waiting(&t, history);
	assert(mt6797_normal_accept_capability(&t, packet, 124, NULL) < 0);
	puts("normal_commands_literal_pio_322_failures_rx_lengths_65536_shared_sequence_tc4=pass");
	return 0;
}
