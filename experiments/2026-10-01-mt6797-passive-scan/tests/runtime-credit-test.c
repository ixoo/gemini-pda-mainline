/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "hif.c"

static struct {
	unsigned int calls, fail_at, words[10], clock_calls;
	bool expire;
	unsigned char *mapping;
} fake;

u64 ktime_get_ns(void)
{
	if (fake.expire && fake.calls == 20 && ++fake.clock_calls >= 2)
		return 1000001000ULL;
	return 1000;
}
void usleep_range(unsigned long low, unsigned long high)
{
	assert(low == 50 && high == 100);
}
static unsigned int reg(unsigned int n)
{
	return n == 0 ? 0x0c : n == 1 ? 0x10 : 0x130 + (n - 2) * 4;
}
int mt6797_test_write(unsigned int value, void *address)
{
	unsigned int n = fake.calls++;
	assert(!(n % 2) && n < 20);
	assert((unsigned char *)address == fake.mapping);
	assert(value == (0x10000004U | (reg(n / 2) << 9)));
	return fake.calls == fake.fail_at ? -EIO : 0;
}
int mt6797_test_read(void *address, unsigned int *value)
{
	unsigned int n = fake.calls++;
	assert(n % 2 && n < 20);
	assert((unsigned char *)address - fake.mapping == 0x1000);
	if (fake.calls == fake.fail_at)
		return -EIO;
	*value = fake.words[n / 2];
	return 0;
}
static struct mt6797_hif *allocate(struct mt6797_init_transaction *transaction)
{
	struct mt6797_hif *hif;
	memset(&fake, 0, sizeof(fake));
	fake.mapping = calloc(1, 0x1004);
	assert(fake.mapping);
	hif = mt6797_hif_alloc(fake.mapping, 0x1004, transaction);
	assert(!IS_ERR(hif));
	hif->firmware_ready = true;
	hif->capability_complete = true;
	hif->tx_status_accounting_baseline = true;
	hif->tx_status_normal_attempted = true;
	assert(!mt6797_normal_admit(&hif->normal, 26, 14,
				   transaction->used_sequences));
	hif->normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	hif->normal.tc4_pending_ffa = 12;
	transaction->used_sequences[0] = 0x7f;
	return hif;
}
static void release(struct mt6797_hif *hif)
{
	mt6797_hif_free(hif);
	free(fake.mapping);
}
static void refuse(unsigned int reason)
{
	struct mt6797_init_transaction transaction = {.phase = MT6797_INIT_IDLE};
	struct mt6797_hif_tx_status status;
	struct mt6797_normal_release account;
	struct mt6797_hif *hif = allocate(&transaction);
	if (reason == 0) hif->tx_status_accounting_baseline = false;
	if (reason == 1) hif->tx_status_normal_attempted = false;
	if (reason == 2) hif->capability_complete = false;
	if (reason == 3) hif->normal.phase = MT6797_NORMAL_CAP_RECEIVED;
	if (reason == 4) hif->normal.phase = MT6797_NORMAL_FAILED;
	if (reason == 5) transaction.phase = MT6797_INIT_POISONED;
	assert(mt6797_hif_reconcile_runtime(hif, 1000001000ULL,
					   &status, &account) == -EIO);
	assert(!fake.calls && !account.released_pages && hif->normal.tc4_free == 14);
	release(hif);
}
static void fault(unsigned int fail_at, int bad_word, bool expire)
{
	struct mt6797_init_transaction transaction = {.phase = MT6797_INIT_IDLE};
	struct mt6797_hif_tx_status status;
	struct mt6797_normal_release account;
	struct mt6797_hif *hif = allocate(&transaction);
	fake.fail_at = fail_at;
	fake.words[9] = 12U << 16;
	if (bad_word >= 0) fake.words[bad_word] = bad_word == 9 ? 13U << 16 : 1;
	fake.expire = expire;
	assert(mt6797_hif_reconcile_runtime(hif, 1000001000ULL,
					   &status, &account) == (expire ? -ETIMEDOUT : -EIO));
	assert(!account.released_pages && hif->normal.tc4_free == 14);
	assert(hif->normal.tc4_pending_ffa == 12);
	assert(hif->normal.phase == MT6797_NORMAL_FAILED);
	assert(transaction.phase == MT6797_INIT_POISONED);
	unsigned int prior = fake.calls;
	assert(mt6797_hif_reconcile_runtime(hif, 1000001000ULL,
					   &status, &account) == -EIO);
	assert(fake.calls == prior);
	release(hif);
}
static void successive(void)
{
	struct mt6797_init_transaction transaction = {.phase = MT6797_INIT_IDLE};
	struct mt6797_hif_tx_status status;
	struct mt6797_normal_release account;
	struct mt6797_hif *hif = allocate(&transaction);
	for (unsigned int n = 0; n < 12; n++) {
		fake.calls = 0;
		fake.words[9] = 1U << 16;
		assert(!mt6797_hif_reconcile_runtime(hif, 1000001000ULL,
						    &status, &account));
		assert(fake.calls == 20 && status.valid_words == 0x3ff);
		assert(account.released_pages == 1 && account.tc4_free == 15 + n);
		assert(account.pending_ffa == 11 - n && !account.pending_cpu);
		assert(transaction.used_sequences[0] == 0x7f);
	}
	/* A new zero snapshot cannot replay a consumed refund. */
	fake.calls = 0; fake.words[9] = 0;
	assert(!mt6797_hif_reconcile_runtime(hif, 1000001000ULL, &status, &account));
	assert(!account.released_pages && account.tc4_free == 26);
	release(hif);
}
int main(void)
{
	successive();
	for (unsigned int n = 0; n < 6; n++) refuse(n);
	for (unsigned int n = 1; n <= 20; n++) fault(n, -1, false);
	for (int n = 2; n <= 9; n++) fault(0, n, false);
	fault(0, -1, true);
	puts("runtime credit: pass; fresh snapshots, retained pending, 20 transfer faults, late expiry");
	return 0;
}
