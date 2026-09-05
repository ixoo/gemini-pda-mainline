/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "../src/hif.c"

struct operation { bool write; unsigned int offset, value; };
static struct {
	struct operation expected[700];
	unsigned int count, calls, fail_at, expire_at, delay_reads, expiry_reads;
	unsigned int sleeps;
	u64 now, deadline;
	u8 *mapping;
	bool pending;
} fake;

u64 ktime_get_ns(void)
{
	if (fake.expire_at == fake.calls && fake.expiry_reads++ >= fake.delay_reads)
		return fake.deadline;
	return fake.now;
}
void usleep_range(unsigned long minimum, unsigned long maximum)
{
	assert(minimum == 50 && maximum == 100);
	fake.sleeps++;
	fake.now += minimum * 1000;
}
static int access_io(bool write, void *address, unsigned int *value)
{
	struct operation *op;
	unsigned int index = fake.calls++;

	if (fake.pending && index >= 6) {
		assert((size_t)((u8 *)address - fake.mapping) == (write ? 0 : 0x1000));
		if (write)
			assert(*value == 0x10012004);
		else
			*value = 0;
		return 0;
	}
	assert(index < fake.count);
	op = &fake.expected[index];
	assert(op->write == write);
	assert((size_t)((u8 *)address - fake.mapping) == op->offset);
	if (write)
		assert(*value == op->value);
	if (fake.fail_at == fake.calls)
		return -EIO;
	if (!write)
		*value = op->value;
	return 0;
}
int mt6797_test_write(unsigned int value, void *address)
{
	return access_io(true, address, &value);
}
int mt6797_test_read(void *address, unsigned int *value)
{
	return access_io(false, address, value);
}
static void add(bool write, unsigned int offset, unsigned int value)
{
	assert(fake.count < 700);
	fake.expected[fake.count++] = (struct operation){write, offset, value};
}
static struct mt6797_hif *fresh(struct mt6797_init_transaction *transaction)
{
	struct mt6797_hif *hif;

	memset(&fake, 0, sizeof(fake));
	fake.mapping = calloc(1, 0x1004);
	assert(fake.mapping);
	fake.now = 1000;
	fake.deadline = 2000;
	fake.expire_at = ~0U;
	*transaction = (struct mt6797_init_transaction){0};
	transaction->free_pages = 104;
	transaction->start_free_pages = 104;
	hif = mt6797_hif_alloc(fake.mapping, 0x1004, transaction);
	assert(!IS_ERR(hif));
	return hif;
}
static void release(struct mt6797_hif *hif)
{
	mt6797_hif_free(hif);
	free(fake.mapping);
}
static void register_tests(void)
{
	const unsigned int registers[] = {0, 4, 0x90};
	const unsigned int words[] = {0x10000004, 0x10000804, 0x10012004};
	unsigned int i, point;

	for (i = 0; i < 3; i++) {
		for (point = 0; point <= 2; point++) {
			struct mt6797_init_transaction transaction;
			struct mt6797_hif *hif = fresh(&transaction);
			u32 value = 0;
			int error;

			add(true, 0, words[i]);
			add(false, 0x1000, 0x12345678);
			fake.fail_at = point;
			error = mt6797_hif_read32(hif, registers[i], fake.deadline, &value);
			assert(error == (point ? -EIO : 0));
			assert(fake.calls == (point ? point : 2));
			assert(value == (point ? 0 : 0x12345678));
			assert(transaction.free_pages == 104 && transaction.start_free_pages == 104);
			if (point) {
				assert(transaction.phase == MT6797_INIT_POISONED);
				assert(mt6797_hif_read32(hif, 0, fake.deadline, &value) == -EIO);
				assert(fake.calls == point);
			}
			release(hif);
		}
	}
	for (point = 0; point <= 2; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u32 value = 7;

		add(true, 0, words[0]); add(false, 0x1000, 0x12345678);
		fake.expire_at = point;
		assert(mt6797_hif_read32(hif, 0, fake.deadline, &value) == -ETIMEDOUT);
		assert(fake.calls == point && value == 0);
		assert(transaction.phase == MT6797_INIT_POISONED);
		release(hif);
	}
}
static const u8 config[] = {
	20,0,0,0x80,1,0xa0,0,19,0x40,0x30,0x20,0x10,1,8,0,0,13,0,0,0x80
};
static void section_trace(void)
{
	unsigned int i;
	const unsigned int config_words[] = {
		0x90006814,0x80000014,0x1300a001,0x10203040,0x801,0x8000000d
	};

	for (i = 0; i < 6; i++) add(true, i ? 0x1000 : 0, config_words[i]);
	add(true, 0, 0x10012004); add(false, 0x1000, 28);
	add(true, 0, 0x1000a020);
	for (i = 0; i < 8; i++) add(false, 0x1000, i == 0 ? 0xe000001c : (i == 1 ? 0x1301 : 0));
	add(true, 0, 0x98006805); add(true, 0x1000, 0xc0000808); add(true, 0x1000, 0xa000);
	for (i = 0; i < 512; i++) add(true, 0x1000, 0x5a5a5a5a);
	for (i = 0; i < 126; i++) add(true, 0x1000, 0);
	add(true, 0, 0x9000680c); add(true, 0x1000, 0xc0000009);
	add(true, 0x1000, 0xa000); add(true, 0x1000, 0x5a);
	assert(fake.count == 662);
}
static void section_tests(void)
{
	u8 data[2049];
	struct mt6797_hif_section_request request = {
		MT6797_SECTION_ORDINARY, config, sizeof(config), 19, data, sizeof(data)
	};
	unsigned int point;

	memset(data, 0x5a, sizeof(data));
	for (point = 0; point <= 662; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif_section_result result;
		struct mt6797_hif *hif = fresh(&transaction);
		int error;

		section_trace(); fake.fail_at = point;
		error = mt6797_hif_download_section(hif, &request, fake.deadline, &result);
		assert(error == (point ? -EIO : 0));
		assert(fake.calls == (point ? point : 662));
		assert(transaction.free_pages == 103 && transaction.start_free_pages == 104);
		assert(transaction.used_sequences[19 / 8] & (1U << (19 % 8)));
		assert(!result.firmware_status);
		if (point) {
			assert(transaction.phase == MT6797_INIT_POISONED);
			assert(result.submitted == (point > 658 ? 2048U : 0U));
			assert(mt6797_hif_download_section(hif, &request, fake.deadline, &result) == -EIO);
			assert(fake.calls == point);
		} else {
			assert(transaction.phase == MT6797_INIT_IDLE && result.submitted == 2049);
		}
		release(hif);
	}
	for (point = 0; point <= 662; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif_section_result result;
		struct mt6797_hif *hif = fresh(&transaction);

		section_trace(); fake.expire_at = point;
		assert(mt6797_hif_download_section(hif, &request, fake.deadline, &result) == -ETIMEDOUT);
		assert(fake.calls == point && transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.free_pages == (point ? 103U : 104U));
		assert(transaction.start_free_pages == 104);
		release(hif);
	}
	{
		struct mt6797_init_transaction transaction;
		struct mt6797_hif_section_result result;
		struct mt6797_hif *hif = fresh(&transaction);

		section_trace(); fake.expire_at = 658; fake.delay_reads = 1;
		assert(mt6797_hif_download_section(hif, &request, fake.deadline, &result) == -ETIMEDOUT);
		assert(fake.calls == 658 && result.submitted == 2048);
		release(hif);
	}
	for (point = 0; point < 5; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif_section_result result;
		struct mt6797_hif *hif = fresh(&transaction);
		int error;

		section_trace();
		if (point == 0) fake.pending = true;
		if (point == 1) fake.expected[7].value = 29;
		if (point == 2) fake.expected[10].value = 0x1401;
		if (point == 3) fake.expected[11].value = 2;
		if (point == 4) transaction.free_pages = 0;
		error = mt6797_hif_download_section(hif, &request, fake.deadline, &result);
		assert(error == (point == 0 ? -ETIMEDOUT : point == 1 ? -EMSGSIZE :
			point == 2 ? -EPROTO : point == 3 ? -EIO : -ENOSPC));
		assert(fake.calls == (point < 2 ? 8U : point < 4 ? 17U : 0U));
		assert(transaction.phase == MT6797_INIT_POISONED && !result.submitted);
		assert(transaction.free_pages == (point == 4 ? 0U : 103U));
		assert(transaction.start_free_pages == 104);
		assert(result.firmware_status == (point == 3 ? 2U : 0U));
		release(hif);
	}
	{
		struct mt6797_init_transaction transaction;
		struct mt6797_hif_section_result result;
		struct mt6797_hif *hif = fresh(&transaction);

		section_trace();
		assert(!mt6797_hif_download_section(hif, &request, fake.deadline, &result));
		assert(mt6797_hif_download_section(hif, &request, fake.deadline, &result) == -EIO);
		assert(fake.calls == 662 && transaction.free_pages == 103);
		assert(transaction.start_free_pages == 104 && transaction.phase == MT6797_INIT_POISONED);
		release(hif);
	}
	for (point = 0; point < 3; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif_section_result result;
		struct mt6797_hif *hif = fresh(&transaction);
		struct mt6797_hif_section_request bad = request;

		if (point == 0) bad.kind = MT6797_SECTION_EMI;
		if (point == 1) bad.length = 1024U * 1024U + 1;
		if (point == 2) bad.config_bytes = 19;
		assert(mt6797_hif_download_section(hif, &bad, fake.deadline, &result) ==
			(point == 2 ? -EPROTO : -EINVAL));
		assert(!fake.calls && transaction.free_pages == 104 && transaction.start_free_pages == 104);
		release(hif);
	}
	for (point = 0; point < sizeof(data); point++) assert(data[point] == 0x5a);
}
static void refusal_tests(void)
{
	struct mt6797_init_transaction transaction;
	struct mt6797_hif *hif = fresh(&transaction);
	struct mt6797_hif_command command;
	u32 value;

	assert(IS_ERR(mt6797_hif_alloc(NULL, 0x1004, &transaction)));
	assert(IS_ERR(mt6797_hif_alloc(fake.mapping, 0x1003, &transaction)));
	assert(IS_ERR(mt6797_hif_alloc(fake.mapping + 1, 0x1004, &transaction)));
	assert(mt6797_hif_read32(hif, 0x34, fake.deadline, &value) == -EINVAL);
	assert(mt6797_hif_encode_command(0x90, MT6797_HIF_READ, MT6797_HIF_PIO_ONLY, 4, 4, &command) == -EINVAL);
	hif->mutex.held = true;
	assert(mt6797_hif_read32(hif, 0, fake.deadline, &value) == -EBUSY);
	hif->mutex.held = false;
	assert(!fake.calls && transaction.phase == MT6797_INIT_IDLE);
	transaction.phase = MT6797_INIT_PAYLOAD;
	assert(mt6797_hif_read32(hif, 0, fake.deadline, &value) == -EIO);
	assert(!fake.calls);
	release(hif);
	for (unsigned int mode = 0; mode < 4; mode++) {
		hif = fresh(&transaction);
		if (mode == 0) transaction.start_free_pages = 105;
		if (mode == 1) transaction.free_pages = 105;
		assert(mt6797_hif_read32(hif, 0,
			mode == 2 ? fake.now + 1000000001ULL :
			mode == 3 ? 0 : fake.deadline, &value) ==
			(mode == 3 ? -ETIMEDOUT : -EINVAL));
		assert(!fake.calls && transaction.phase == MT6797_INIT_POISONED);
		release(hif);
	}
}
int main(void)
{
	register_tests(); section_tests(); refusal_tests();
	puts("register_literals=3 register_faults=6 section_io_faults=662 scalar_deadline_boundaries=666 next_chunk_deadline=pass");
	puts("actual_core_section_trace_credit_poison_ack_padding_no_retry=pass");
	return 0;
}
