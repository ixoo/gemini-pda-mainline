/* SPDX-License-Identifier: GPL-2.0-only */
#define main previous_hif_tests
#include "test-hif.c"
#undef main

static const u8 start_command[16] = {
	16, 0, 0, 0x80, 2, 0xa0, 0, 20, 1, 0, 0, 0, 0x40, 0x30, 0x20, 0x10
};

static void start_trace(void)
{
	add(true, 0, 0x90006810);
	add(true, 0x1000, 0x80000010);
	add(true, 0x1000, 0x1400a002);
	add(true, 0x1000, 1);
	add(true, 0x1000, 0x10203040);
}

static void ready_trace(u32 value)
{
	add(true, 0, 0x10000004);
	add(false, 0x1000, value);
}

static int submit(struct mt6797_hif *hif)
{
	return mt6797_hif_start_submit(hif, start_command, 16, 20, fake.deadline);
}

static void start_faults(void)
{
	for (unsigned int point = 1; point <= 5; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u32 wcir = ~0U;

		start_trace();
		fake.fail_at = point;
		assert(submit(hif) == -EIO);
		assert(fake.calls == point && !fake.sleeps);
		assert(transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.free_pages == 104 && transaction.start_free_pages == 103);
		assert(transaction.used_sequences[2] == 0x10);
		assert(submit(hif) < 0);
		assert(mt6797_hif_start_observe_ready(hif, &wcir) < 0 && !wcir);
		assert(fake.calls == point);
		release(hif);
	}
	for (unsigned int point = 0; point <= 5; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);

		start_trace();
		fake.expire_at = point;
		assert(submit(hif) == -ETIMEDOUT);
		assert(fake.calls == point && transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.free_pages == 104);
		assert(transaction.start_free_pages == (point ? 103U : 104U));
		assert(submit(hif) < 0 && fake.calls == point);
		release(hif);
	}
	{
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);

		start_trace();
		fake.expire_at = 5; fake.delay_reads = 1;
		assert(submit(hif) == -ETIMEDOUT);
		assert(fake.calls == 5 && transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.start_free_pages == 103 && transaction.free_pages == 104);
		release(hif);
	}
	for (unsigned int point = 0; point < 3; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u32 wcir = ~0U;

		start_trace(); ready_trace(1U << 21);
		assert(!submit(hif));
		fake.expire_at = 5 + point;
		assert(mt6797_hif_start_observe_ready(hif, &wcir) == -ETIMEDOUT);
		assert(!wcir && fake.calls == 5 + point);
		assert(transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.free_pages == 104 && transaction.start_free_pages == 103);
		release(hif);
	}
	for (unsigned int point = 6; point <= 7; point++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u32 wcir = ~0U;

		start_trace(); ready_trace(1U << 21);
		assert(!submit(hif));
		fake.fail_at = point;
		assert(mt6797_hif_start_observe_ready(hif, &wcir) == -EIO);
		assert(!wcir && fake.calls == point);
		assert(transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.free_pages == 104 && transaction.start_free_pages == 103);
		release(hif);
	}
}

static void start_success(void)
{
	struct mt6797_init_transaction transaction;
	struct mt6797_hif *hif = fresh(&transaction);
	u32 wcir;
	u8 next[16];

	start_trace(); ready_trace(0xffdfffffU); ready_trace(1U << 21);
	assert(!submit(hif) && fake.calls == 5 && !hif->firmware_ready);
	assert(transaction.phase == MT6797_START_READY);
	assert(mt6797_hif_start_observe_ready(hif, &wcir) == -EAGAIN);
	assert(wcir == 0xffdfffffU && transaction.phase == MT6797_START_READY);
	assert(!mt6797_hif_start_observe_ready(hif, &wcir));
	assert(wcir == (1U << 21) && transaction.phase == MT6797_INIT_IDLE);
	assert(fake.calls == 9 && !fake.sleeps && hif->firmware_ready);
	assert(transaction.free_pages == 104 && transaction.start_free_pages == 103);
	memcpy(next, start_command, 16); next[7] = 21;
	assert(mt6797_hif_start_submit(hif, next, 16, 21, fake.deadline) < 0);
	assert(fake.calls == 9 && transaction.phase == MT6797_INIT_POISONED);
	release(hif);

	/* Actual CONFIG/ACK/PDA then START share history, never TC4/TC0 debits. */
	{
		u8 data[2049];
		struct mt6797_hif_section_request request = {
			MT6797_SECTION_ORDINARY, config, sizeof(config), 19, data, sizeof(data)
		};
		struct mt6797_hif_section_result result;

		memset(data, 0x5a, sizeof(data));
		hif = fresh(&transaction);
		section_trace(); start_trace(); ready_trace(1U << 21);
		assert(!mt6797_hif_download_section(hif, &request, fake.deadline, &result));
		assert(result.submitted == 2049);
		assert(!submit(hif));
		assert(!mt6797_hif_start_observe_ready(hif, &wcir));
		assert(transaction.free_pages == 103 && transaction.start_free_pages == 103);
		assert(transaction.used_sequences[2] == 0x18);
		assert(fake.calls == 669);
		assert(mt6797_hif_download_section(hif, &request, fake.deadline, &result) < 0);
		assert(fake.calls == 669);
		release(hif);
	}
}

static void start_refusals(void)
{
	for (unsigned int mode = 0; mode < 10; mode++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u8 command[16];
		u32 wcir;
		int error;

		memcpy(command, start_command, 16);
		if (mode == 0) transaction.start_free_pages = 0;
		if (mode == 1) transaction.used_sequences[2] = 0x10;
		if (mode == 2) command[8] = 2;
		if (mode == 3) command[4] = 1;
		if (mode == 4) transaction.phase = MT6797_INIT_PAYLOAD;
		if (mode == 5) transaction.start_free_pages = 105;
		if (mode == 6) command[7] = 21;
		error = mt6797_hif_start_submit(hif, mode == 7 ? NULL : command,
			mode == 8 ? 15 : 16, mode == 9 ? 256 : 20, fake.deadline);
		assert(error < 0 && !fake.calls);
		assert(transaction.phase == MT6797_INIT_POISONED);
		assert(transaction.free_pages == 104);
		assert(transaction.start_free_pages == (mode == 0 ? 0U : mode == 5 ? 105U : 104U));
		assert(mt6797_hif_start_observe_ready(hif, &wcir) < 0 && !fake.calls);
		release(hif);
	}
	for (unsigned int mode = 0; mode < 5; mode++) {
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u32 wcir = ~0U;

		start_trace(); ready_trace(0);
		if (mode == 0) {
			assert(mt6797_hif_start_observe_ready(hif, &wcir) < 0);
			assert(!fake.calls);
		} else {
			assert(!submit(hif));
			if (mode == 1) {
				assert(mt6797_hif_start_observe_ready(hif, &wcir) == -EAGAIN);
				fake.now = fake.deadline;
				assert(mt6797_hif_start_observe_ready(hif, &wcir) == -ETIMEDOUT);
				assert(fake.calls == 7);
			} else if (mode == 2) {
				assert(mt6797_hif_read32(hif, 0, fake.deadline + 1, &wcir) == -EINVAL);
				assert(fake.calls == 5);
			} else if (mode == 3) {
				mt6797_init_abort(&transaction); /* External owner loss. */
				assert(mt6797_hif_start_observe_ready(hif, &wcir) < 0);
				assert(fake.calls == 5);
			} else {
				fake.expected[6].value = 1U << 21;
				fake.expire_at = 7; fake.delay_reads = 1;
				assert(mt6797_hif_start_observe_ready(hif, &wcir) == -ETIMEDOUT);
				assert(fake.calls == 7 && !hif->firmware_ready);
			}
		}
		assert(!wcir && transaction.phase == MT6797_INIT_POISONED);
		release(hif);
	}
	{
		struct mt6797_init_transaction transaction;
		struct mt6797_hif *hif = fresh(&transaction);
		u32 wcir;

		hif->mutex.held = true;
		assert(submit(hif) == -EBUSY && !hif->start_attempted);
		assert(mt6797_hif_start_observe_ready(hif, &wcir) == -EBUSY);
		hif->mutex.held = false;
		assert(!fake.calls && transaction.phase == MT6797_INIT_IDLE);
		transaction.free_pages = 0;
		start_trace();
		assert(!submit(hif));
		assert(!transaction.free_pages && transaction.start_free_pages == 103);
		release(hif);
	}
}

int main(void)
{
	assert(!previous_hif_tests());
	start_faults(); start_success(); start_refusals();
	puts("actual_start_literals=5 start_io_faults=5 ready_io_faults=2 deadline_boundaries=9");
	puts("post_transfer_guard_expiry=2 pending_vs_ready_same_deadline_no_ack_no_retry_no_refund_owner_abort=pass");
	return 0;
}
