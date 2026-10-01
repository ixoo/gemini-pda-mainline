/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "../drivers/net/wireless/mediatek/mt6797/hif.c"

static struct {
	unsigned int calls, fail_at, mode;
	u64 now;
	u8 *mapping;
} fake;

u64 ktime_get_ns(void) { return fake.now; }
void usleep_range(unsigned long minimum, unsigned long maximum)
{
	assert(minimum == 50 && maximum == 100);
	fake.now += minimum * 1000;
}
static unsigned int reply_word(unsigned int index)
{
	switch (index) {
	case 0: return 0xe000007c;
	case 1: return 0x00000401;
	case 2: return 0x03021234;
	case 3: return 0x09070504;
	case 6: return 0xfffe0000;
	default: return 0;
	}
}
static int access_io(bool write, void *address, unsigned int *value)
{
	unsigned int i = fake.calls++, expected = 0;
	bool expected_write = true;
	unsigned int offset = 0;

	if (fake.mode == 5) {
		static const unsigned int start_words[7] = {
			0x90006810, 0x80000010, 0x0300a002, 0, 0,
			0x10000004, 0x00300279,
		};

		assert(i < 7);
		expected_write = i != 6;
		offset = i == 0 || i == 5 ? 0 : 0x1000;
		expected = start_words[i];
	} else if (fake.mode == 4 && i >= 34) {
		assert(i < 38);
		expected_write = !(i & 1);
		offset = expected_write ? 0 : 0x1000;
		expected = expected_write ? 0x10012004 : 0;
	} else if (i == 0 || i == 34)
		expected = 0x10012004;
	else if (i == 1 || i == 35) {
		expected_write = false;
		offset = 0x1000;
		expected = i == 1 ?
			(fake.mode == 1 ? 0x00010059 :
			 fake.mode == 6 ? 0x00000059 : 0) :
			(fake.mode == 2 ? 0x007b0000 :
			 fake.mode == 4 ? 0 :
			 fake.mode == 6 ? 0x007c0059 : 0x007c0000);
	} else if (i == 2)
		expected = 0x9000687c;
	else if (i >= 3 && i <= 33) {
		offset = 0x1000;
		expected = i == 3 ? 0x8000007c :
			i == 4 ? 0x0400a080 : 0;
	} else if (i == 36)
		expected = 0x1000a880;
	else {
		assert(i >= 37 && i < 69);
		expected_write = false;
		offset = 0x1000;
		expected = reply_word(i - 37);
		if (fake.mode == 3 && i == 38)
			expected ^= 0x00000100;
	}
	assert(write == expected_write);
	assert((size_t)((u8 *)address - fake.mapping) == offset);
	if (write)
		assert(*value == expected);
	else
		*value = expected;
	return fake.calls == fake.fail_at ? -EIO : 0;
}
int mt6797_test_write(unsigned int value, void *address)
{
	return access_io(true, address, &value);
}
int mt6797_test_read(void *address, unsigned int *value)
{
	return access_io(false, address, value);
}
static void exercise(unsigned int mode, unsigned int fail_at)
{
	struct mt6797_init_transaction transaction = {
		.phase = MT6797_START_READY,
		.free_pages = 102, .start_free_pages = 103,
	};
	struct mt6797_normal_capability capability;
	struct mt6797_capability_trace trace;
	struct mt6797_hif *hif;
	int error;

	memset(&fake, 0, sizeof(fake));
	fake.mapping = calloc(1, 0x1004);
	assert(fake.mapping);
	fake.now = 1000;
	fake.mode = mode;
	fake.fail_at = fail_at;
	transaction.used_sequences[0] = 0x0e;
	assert(!mt6797_start_observe_ready(&transaction, 0x00300279));
	assert(transaction.phase == MT6797_INIT_IDLE);
	hif = mt6797_hif_alloc(fake.mapping, 0x1004, &transaction);
	assert(!IS_ERR(hif));
	hif->start_attempted = true;
	hif->firmware_ready = true;
	error = mt6797_hif_query_capability(hif, 4,
					    mode == 4 ? 101000ULL : 1000001000ULL,
					    &capability, &trace);
	if ((!mode || mode == 6) && !fail_at) {
		assert(!error && fake.calls == 69);
		assert(trace.stage == MT6797_CAP_DONE);
		assert(trace.pre_valid &&
		       trace.pre_wrplr == (mode == 6 ? 0x00000059 : 0));
		assert(trace.post_valid &&
		       trace.post_wrplr == (mode == 6 ? 0x007c0059 : 0x007c0000));
		assert(trace.tx_complete && trace.tx_bytes == 124);
		assert(trace.rx_complete && trace.rx_bytes == 128);
		assert(trace.event_length == 124 &&
		       trace.packet_type == 0xe000 &&
		       trace.event_id == 1 && trace.event_sequence == 4);
		assert(capability.product == 0x1234);
		assert(capability.firmware_own == 0x0302);
		assert(capability.firmware_peer == 0x0504);
		assert(capability.hw_5g_disabled == 7);
		assert(capability.eeprom_used == 9);
		assert(capability.rf_cal_fail == 0xfe);
		assert(capability.bb_cal_fail == 0xff);
		assert(transaction.phase == MT6797_INIT_IDLE);
	} else {
		assert(error && !capability.product);
		if (mode == 1 && !fail_at)
			assert(trace.stage == MT6797_CAP_PRE_WRPLR &&
			       trace.pre_valid && trace.pre_wrplr == 0x00010059 &&
			       !trace.tx_setup);
		if (mode == 2 && !fail_at)
			assert(trace.stage == MT6797_CAP_REPLY_SPAN &&
			       trace.post_valid && trace.post_wrplr == 0x007b0000 &&
			       !trace.rx_setup);
		if (mode == 3 && !fail_at)
			assert(trace.stage == MT6797_CAP_PARSE &&
			       trace.rx_complete && trace.event_sequence == 5);
		if (mode == 4)
			assert(error == -ETIMEDOUT && fake.calls == 38 &&
			       trace.stage == MT6797_CAP_POST_WRPLR &&
			       trace.post_valid && !trace.post_wrplr);
		assert(transaction.phase == MT6797_INIT_POISONED);
		if (fail_at)
			assert(fake.calls == fail_at);
	}
	assert(transaction.used_sequences[0] == (fail_at <= 2 && fail_at ?
		0x0e : mode == 1 ? 0x0e : 0x1e));
	{
		struct mt6797_capability_trace second_trace;
		int second = mt6797_hif_query_capability(hif, 5, 1000001000ULL,
							 &capability, &second_trace);
		if (second != -EIO)
			fprintf(stderr, "mode=%u fail_at=%u second=%d\n", mode,
				fail_at, second);
		assert(second == -EIO);
	}
	mt6797_hif_free(hif);
	free(fake.mapping);
}
static void start_then_capability(void)
{
	static const u8 start[16] = { 16, 0, 0, 0x80, 2, 0xa0, 0, 3 };
	struct mt6797_init_transaction transaction = {
		.phase = MT6797_INIT_IDLE,
		.free_pages = 102, .start_free_pages = 104,
	};
	struct mt6797_normal_capability capability;
	struct mt6797_capability_trace trace;
	struct mt6797_hif *hif;
	u32 wcir = 0;

	memset(&fake, 0, sizeof(fake));
	fake.mapping = calloc(1, 0x1004);
	assert(fake.mapping);
	fake.now = 1000;
	fake.mode = 5;
	transaction.used_sequences[0] = 0x06;
	hif = mt6797_hif_alloc(fake.mapping, 0x1004, &transaction);
	assert(!IS_ERR(hif));
	assert(!mt6797_hif_start_submit(hif, start, sizeof(start), 3,
					    1000001000ULL));
	assert(fake.calls == 5 && !hif->firmware_ready);
	assert(!mt6797_hif_start_observe_ready(hif, &wcir));
	assert(fake.calls == 7 && wcir == 0x00300279);
	assert(hif->firmware_ready && transaction.phase == MT6797_INIT_IDLE);
	assert(transaction.start_free_pages == 103 &&
	       transaction.used_sequences[0] == 0x0e);
	fake.mode = 0;
	fake.calls = 0;
	assert(!mt6797_hif_query_capability(hif, 4, 1000001000ULL,
					     &capability, &trace));
	assert(fake.calls == 69 && trace.stage == MT6797_CAP_DONE);
	assert(capability.product == 0x1234);
	mt6797_hif_free(hif);
	free(fake.mapping);
}

static void reject_unready_phase(bool firmware_ready)
{
	struct mt6797_init_transaction transaction = {
		.phase = MT6797_START_READY,
		.free_pages = 102, .start_free_pages = 103,
	};
	struct mt6797_normal_capability capability;
	struct mt6797_capability_trace trace;
	struct mt6797_hif *hif;
	u8 *mapping = calloc(1, 0x1004);

	assert(mapping);
	memset(&fake, 0, sizeof(fake));
	fake.mapping = mapping;
	fake.now = 1000;
	hif = mt6797_hif_alloc(mapping, 0x1004, &transaction);
	assert(!IS_ERR(hif));
	hif->start_attempted = true;
	hif->firmware_ready = firmware_ready;
	assert(mt6797_hif_query_capability(hif, 4, 1000001000ULL,
					   &capability, &trace) == -EIO);
	assert(trace.stage == MT6797_CAP_ENTER && !fake.calls);
	assert(transaction.phase == MT6797_START_READY);
	mt6797_hif_free(hif);
	free(mapping);
}

int main(void)
{
	unsigned int i;

	reject_unready_phase(false);
	reject_unready_phase(true);
	start_then_capability();
	exercise(0, 0);
	for (i = 1; i <= 69; i++)
		exercise(0, i);
	exercise(1, 0);
	exercise(2, 0);
	exercise(3, 0);
	exercise(4, 0);
	exercise(6, 0);
	puts("post-START idle admission, literal PIO, 69 access faults and malformed reply: pass");
	return 0;
}
