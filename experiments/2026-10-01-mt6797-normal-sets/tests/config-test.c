/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "normal_command.h"
#include "hif_pio.h"

struct fake_io {
	unsigned int setup, calls, fail_at;
	unsigned char data[1024];
};

static int write_word(void *context, unsigned int offset, unsigned int value)
{
	struct fake_io *fake = context;
	unsigned int index = fake->calls++;

	if (!index) {
		assert(offset == 0 && value == fake->setup);
	} else {
		unsigned int byte;

		assert(offset == 0x1000 && 4 * index <= sizeof(fake->data));
		for (byte = 0; byte < 4; byte++)
			fake->data[4 * (index - 1) + byte] = value >> (8 * byte);
	}
	return fake->calls == fake->fail_at ? -EIO : 0;
}

static void send_config(struct mt6797_normal_transaction *normal,
			enum mt6797_normal_config_kind kind, size_t length,
			unsigned int sequence)
{
	unsigned char payload[528], frame[1024];
	struct mt6797_hif_pio_result result;
	struct mt6797_hif_command command;
	struct fake_io fake = {0};
	struct mt6797_hif_pio_io io = {.context = &fake, .write = write_word};
	unsigned int before = normal->tc4_free;
	size_t i;

	for (i = 0; i < length; i++)
		payload[i] = (unsigned char)(i + sequence);
	memset(frame, 0xa5, sizeof(frame));
	assert(!mt6797_normal_prepare_config(normal, kind, sequence, payload,
						length, frame, sizeof(frame), &command));
	assert(normal->phase == MT6797_NORMAL_CONFIG_TX);
	assert(normal->tc4_free == before - (8 + length + 127) / 128);
	assert((normal->used_sequences[sequence / 8] &
		(1U << (sequence % 8))) != 0);
	assert(mt6797_normal_le16(frame) == 8 + length);
	assert(frame[2] == 0 && frame[3] == 0x80 && frame[4] == kind &&
		frame[5] == 0xa0 && frame[6] == 1 && frame[7] == sequence);
	assert(!memcmp(frame + 8, payload, length));
	for (i = 8 + length; i < command.transfer_bytes; i++)
		assert(!frame[i]);
	fake.setup = command.word;
	assert(!mt6797_hif_pio_transfer(&io, 0x34, MT6797_HIF_WRITE,
					    frame, 8 + length, sizeof(frame), &result));
	assert(result.setup_submitted && result.transfer_complete &&
	       result.data_bytes == command.transfer_bytes);
	assert(fake.calls == 1 + command.transfer_bytes / 4);
	assert(!memcmp(fake.data, frame, command.transfer_bytes));
	assert(!mt6797_normal_submitted(normal, 0));
	assert(normal->phase == MT6797_NORMAL_CAP_RECEIVED);
}

static void worst_case_sequence(void)
{
	struct mt6797_normal_transaction normal = {0};
	unsigned char history[32] = {0}, nvram[512] = {0};
	unsigned char frame[1024];
	struct mt6797_hif_command command;
	unsigned int sequence = 5;

	history[0] = 0x1e; /* INIT sequences 1-3 and capability 4. */
	assert(!mt6797_normal_admit(&normal, 26, 25, history));
	/* Model the state after the real capability reply. */
	normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	send_config(&normal, MT6797_NORMAL_TX_PWR, 40, sequence++);
	send_config(&normal, MT6797_NORMAL_EDGE_5G, 4, sequence++);
	send_config(&normal, MT6797_NORMAL_CHANNEL_OFFSET, 12, sequence++);
	send_config(&normal, MT6797_NORMAL_AC_PWR, 12, sequence++);
	send_config(&normal, MT6797_NORMAL_DOMAIN, 56, sequence++);
	send_config(&normal, MT6797_NORMAL_DOMAIN, 56, sequence++);
	send_config(&normal, MT6797_NORMAL_COUNTRY_POWER, 528, sequence++);
	send_config(&normal, MT6797_NORMAL_CHANNEL_OFFSET, 12, sequence++);
	send_config(&normal, MT6797_NORMAL_RSSI, 2, sequence++);
	send_config(&normal, MT6797_NORMAL_EDGE_2G, 4, sequence++);
	send_config(&normal, MT6797_NORMAL_AC_PWR, 12, sequence++);
	assert(normal.tc4_free == 10 && sequence == 16);
	assert(!mt6797_normal_prepare(&normal, MT6797_NORMAL_NVRAM,
		sequence, nvram, sizeof(nvram), frame, sizeof(frame), &command));
	assert(normal.tc4_free == 5 && normal.phase == MT6797_NORMAL_NVRAM_TX);
	assert(mt6797_normal_submitted(&normal, 0) == 0);
	assert(normal.phase == MT6797_NORMAL_NVRAM_SUBMITTED);
	assert(mt6797_normal_prepare_config(&normal, MT6797_NORMAL_DOMAIN,
		17, frame, 56, frame, sizeof(frame), &command) == -EIO);
	assert(normal.phase == MT6797_NORMAL_FAILED);
}

static void refusals(void)
{
	static const struct { enum mt6797_normal_config_kind kind; size_t length; } invalid[] = {
		{MT6797_NORMAL_DOMAIN, 55}, {MT6797_NORMAL_TX_PWR, 39},
		{MT6797_NORMAL_EDGE_2G, 3}, {MT6797_NORMAL_EDGE_5G, 5},
		{MT6797_NORMAL_CHANNEL_OFFSET, 11}, {MT6797_NORMAL_AC_PWR, 13},
		{MT6797_NORMAL_RSSI, 1}, {MT6797_NORMAL_COUNTRY_POWER, 15},
		{MT6797_NORMAL_COUNTRY_POWER, 529},
		{MT6797_NORMAL_COUNTRY_POWER, 25},
		{(enum mt6797_normal_config_kind)0x99, 56},
	};
	unsigned int index;
	for (index = 0; index < sizeof(invalid) / sizeof(invalid[0]); index++) {
		struct mt6797_normal_transaction normal = {0};
		unsigned char history[32] = {0}, payload[529] = {0};
		unsigned char frame[1024];
		struct mt6797_hif_command command;

		assert(!mt6797_normal_admit(&normal, 26, 25, history));
		normal.phase = MT6797_NORMAL_CAP_RECEIVED;
		memset(frame, 0xa5, sizeof(frame));
		assert(mt6797_normal_prepare_config(&normal, invalid[index].kind,
			5, payload, invalid[index].length, frame, sizeof(frame),
			&command) == -EINVAL);
		assert(normal.phase == MT6797_NORMAL_CAP_RECEIVED &&
		       normal.tc4_free == 25 && !history[0]);
		assert(!command.word && frame[0] == 0xa5);
	}
}

static void state_and_transport_refusals(void)
{
	struct mt6797_normal_transaction normal = {0};
	unsigned char history[32] = {0}, payload[56] = {0};
	unsigned char frame[1024];
	struct mt6797_hif_command command;
	struct mt6797_hif_pio_result result;
	struct fake_io fake = {0};
	struct mt6797_hif_pio_io io = {.context = &fake, .write = write_word};

	assert(!mt6797_normal_admit(&normal, 26, 0, history));
	normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	memset(frame, 0xa5, sizeof(frame));
	assert(mt6797_normal_prepare_config(&normal, MT6797_NORMAL_DOMAIN, 5,
		payload, sizeof(payload), frame, sizeof(frame), &command) == -ENOSPC);
	assert(normal.phase == MT6797_NORMAL_CAP_RECEIVED && !history[0] &&
	       !normal.tc4_free && frame[0] == 0xa5);
	normal.tc4_free = 25;
	history[0] = 1U << 5;
	assert(mt6797_normal_prepare_config(&normal, MT6797_NORMAL_DOMAIN, 5,
		payload, sizeof(payload), frame, sizeof(frame), &command) == -EIO);
	assert(normal.phase == MT6797_NORMAL_FAILED && normal.tc4_free == 25);
	assert(frame[0] == 0xa5);

	normal = (struct mt6797_normal_transaction){0};
	memset(history, 0, sizeof(history));
	assert(!mt6797_normal_admit(&normal, 26, 25, history));
	normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	assert(!mt6797_normal_prepare_config(&normal, MT6797_NORMAL_DOMAIN, 5,
		payload, sizeof(payload), frame, sizeof(frame), &command));
	assert(normal.tc4_free == 24 && history[0] == (1U << 5));
	fake.setup = command.word;
	fake.fail_at = 2; /* setup succeeded; first FIFO data write failed. */
	assert(mt6797_hif_pio_transfer(&io, 0x34, MT6797_HIF_WRITE,
					    frame, 64, sizeof(frame), &result) == -EIO);
	assert(result.setup_submitted && !result.transfer_complete);
	assert(mt6797_normal_submitted(&normal, -EIO) == -EIO);
	assert(normal.phase == MT6797_NORMAL_FAILED && normal.tc4_free == 24);
	assert(history[0] == (1U << 5));

	normal = (struct mt6797_normal_transaction){0};
	memset(history, 0, sizeof(history));
	assert(!mt6797_normal_admit(&normal, 26, 25, history));
	assert(mt6797_normal_prepare_config(&normal, MT6797_NORMAL_DOMAIN, 5,
		payload, sizeof(payload), frame, sizeof(frame), &command) == -EIO);
	assert(normal.phase == MT6797_NORMAL_FAILED && !history[0]);
}

int main(void)
{
	worst_case_sequence();
	refusals();
	state_and_transport_refusals();
	puts("selected normal config sequence and refusals: pass");
	return 0;
}
