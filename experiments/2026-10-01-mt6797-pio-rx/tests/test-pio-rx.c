/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "hif.c"

static struct {
	u8 *base;
	u64 now;
	unsigned int calls, fail_at, words, logical, port;
	unsigned int post, header_delta;
	bool copy_allowed;
} mock;

u64 ktime_get_ns(void) { return mock.now; }
void usleep_range(unsigned long min, unsigned long max)
{
	(void)min; (void)max;
	assert(false);
}
static unsigned int word_at(unsigned int index)
{
	unsigned int offset = index * 4, word = 0;
	unsigned int byte;

	for (byte = 0; byte < 4; byte++) {
		unsigned int pos = offset + byte;
		unsigned int value = pos == 0 ? (mock.logical + mock.header_delta) & 255 :
			pos == 1 ? (mock.logical + mock.header_delta) >> 8 :
			pos == 2 ? 0 : pos == 3 ? 0xe0 : pos & 255;

		word |= value << (byte * 8);
	}
	return word;
}
static int io(bool write, void *address, unsigned int *value)
{
	unsigned int index = mock.calls++;
	unsigned int setup;
	struct mt6797_hif_command command;

	assert((u8 *)address - mock.base == (write ? 0 : 0x1000));
	if (index == 0 || (mock.copy_allowed && index == mock.words + 3)) {
		assert(write && *value == 0x10012004);
	} else if (index == 1) {
		assert(!write);
		*value = mock.port ? mock.logical << 16 : mock.logical;
	} else if (mock.copy_allowed && index == 2) {
		assert(!mt6797_hif_encode_command(mock.port ? 0x54 : 0x50,
			MT6797_HIF_READ, MT6797_HIF_PIO_ONLY,
			mock.logical + 4, 2560, &command));
		setup = command.word;
		assert(write && *value == setup);
	} else if (mock.copy_allowed && index < mock.words + 3) {
		assert(!write);
		*value = word_at(index - 3);
	} else {
		assert(mock.copy_allowed && index == mock.words + 4 && !write);
		*value = mock.post;
	}
	return mock.fail_at == mock.calls ? -EIO : 0;
}
int mt6797_test_write(unsigned int value, void *address)
{
	return io(true, address, &value);
}
int mt6797_test_read(void *address, unsigned int *value)
{
	return io(false, address, value);
}
static void check(unsigned int port, unsigned int length, size_t capacity,
		  unsigned int fail_at, unsigned int header_delta)
{
	struct mt6797_init_transaction txn = { .phase = MT6797_INIT_IDLE,
		.free_pages = 104, .start_free_pages = 104 };
	struct mt6797_hif_rx_result result;
	struct mt6797_hif_command command;
	struct mt6797_hif *hif;
	u8 out[2352];
	unsigned int i, expected_calls;
	int error;

	memset(&mock, 0, sizeof(mock));
	mock.base = calloc(1, 0x1004);
	assert(mock.base);
	mock.now = 1000;
	mock.port = port;
	mock.logical = length;
	mock.header_delta = header_delta;
	mock.fail_at = fail_at;
	mock.copy_allowed = length >= 4 && length <= 2352 && capacity >= length;
	if (mock.copy_allowed) {
		assert(!mt6797_hif_encode_command(port ? 0x54 : 0x50,
				MT6797_HIF_READ, MT6797_HIF_PIO_ONLY,
				length + 4, 2560, &command));
		mock.words = command.transfer_bytes / 4;
	}
	mock.post = 0;
	expected_calls = mock.copy_allowed ? mock.words + 5 : 2;
	memset(out, 0xa5, sizeof(out));
	hif = mt6797_hif_alloc(mock.base, 0x1004, &txn);
	assert(!IS_ERR(hif));
	hif->firmware_ready = true;
	hif->capability_complete = true;
	hif->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	error = mt6797_hif_receive_packet(hif, port, 1000001000ULL,
					 out, capacity, &result);
	if (fail_at) {
		assert(error == -EIO && mock.calls == fail_at);
		assert(txn.phase == MT6797_INIT_POISONED);
		assert(hif->normal.phase == MT6797_NORMAL_FAILED);
	} else if (!length) {
		assert(error == -EAGAIN && mock.calls == 2);
		assert(txn.phase == MT6797_INIT_IDLE);
	} else if (length < 4 || length > 2352 || header_delta) {
		assert(error == -EPROTO && mock.calls == (header_delta ? mock.words + 3 : expected_calls));
		assert(txn.phase == MT6797_INIT_POISONED);
	} else if (capacity < length) {
		assert(error == -ENOSPC && mock.calls == 2);
		assert(txn.phase == MT6797_INIT_IDLE);
	} else {
		assert(!error && mock.calls == expected_calls);
		assert(result.pre_valid && result.rx_setup && result.rx_complete &&
			result.post_valid && result.logical_bytes == length &&
			result.staging_bytes == mock.words * 4 &&
			result.packet_type == 0xe000);
		assert(txn.phase == MT6797_INIT_IDLE);
		for (i = 0; i < length; i++)
			assert(out[i] == ((word_at(i / 4) >> ((i % 4) * 8)) & 255));
	}
	if (error)
		for (i = 0; i < sizeof(out); i++) assert(out[i] == 0xa5);
	mt6797_hif_free(hif);
	free(mock.base);
}
int main(void)
{
	unsigned int i;

	check(0, 0, 2352, 0, 0);
	check(1, 0, 2352, 0, 0);
	check(0, 80, 79, 0, 0);
	check(0, 1, 2352, 0, 0);
	check(0, 2353, 2352, 0, 0);
	check(0, 80, 2352, 0, 1);
	check(0, 80, 2352, 0, 0);
	check(1, 4, 2352, 0, 0);
	check(1, 2352, 2352, 0, 0);
	for (i = 1; i <= 26; i++) check(0, 80, 2352, i, 0);
	puts("bounded PIO RX: pass");
	return 0;
}
