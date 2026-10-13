/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual extracted mac.c step + actual hif.c. No kernel concurrency claim. */
#define MT6797_HIF_HOST_TEST
#include "hif.c"
#define RX_FLAG_DECRYPTED (1U << 0)
#define RX_FLAG_IV_STRIPPED (1U << 1)
#define RX_FLAG_PN_VALIDATED (1U << 2)
#define RX_FLAG_MMIC_STRIPPED (1U << 3)
#define RX_FLAG_MIC_STRIPPED (1U << 4)
#define RX_FLAG_ALLOW_SAME_PN (1U << 5)
#define RX_FLAG_NO_SIGNAL_VAL (1U << 6)
#include "native-diag.h"

#define NSEC_PER_MSEC 1000000ULL
#define min_t(type, a, b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define dev_info(...) ((void)0)
static bool native_delivery_diag = true;
static u64 clock_ns;
static unsigned int calls, fail_at, expire_at;
static u8 mapping[0x1004], emitted[24];
static bool ended;

struct mt6797_mac {
	struct mt6797_hif *hif;
	u64 native_diag_started, join_data_deadline, join_credit_deadline, join_deadline;
	unsigned int native_diag_total, native_diag_native, native_diag_bytes;
	unsigned int sequence, join_page_debt, join_key_pairwise, join_key_group;
	unsigned char native_diag_state;
	bool join_data_phase, join_data_ended, join_credit_pending, join_inflight;
	bool closing, native_diag_sample_done, native_diag_engaged;
	int first_error, join_credit_done;
};
static void reinit_completion(int *completion) { *completion = 0; }
static void mt6797_mac_join_end_data(struct mt6797_mac *mac, const char *reason)
{ (void)mac; (void)reason; ended = true; }
#include "native-step.inc"

u64 ktime_get_ns(void) { return clock_ns; }
void usleep_range(unsigned long minimum, unsigned long maximum)
{ (void)minimum; (void)maximum; assert(false); }
int mt6797_test_read(void *address, unsigned int *value)
{ (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_write(unsigned int value, void *address)
{
	assert(calls < 7); /* one command word + six payload words, no retry */
	assert(address == mapping + (calls ? 0x1000 : 0));
	if (calls) {
		unsigned int offset = (calls - 1) * 4;
		for (unsigned int i = 0; i < 4; i++)
			emitted[offset + i] = value >> (8 * i);
	}
	calls++;
	if (calls == expire_at)
		clock_ns += 100 * NSEC_PER_MSEC;
	return calls == fail_at ? -EIO : 0;
}

static void exercise(bool enable, u64 remaining, unsigned int fault,
		     unsigned int expiry, bool old)
{
	struct mt6797_init_transaction transaction = { .phase = MT6797_INIT_IDLE };
	u8 history[32] = {0};
	struct mt6797_hif hif = {
		.transaction = &transaction, .firmware_ready = true,
		.capability_complete = true, .base = mapping,
	};
	struct mt6797_mac mac = {
		.hif = &hif, .sequence = 19,
		.native_diag_state = enable ? MT6797_ND_IDLE : MT6797_ND_ACTIVE,
		.join_data_phase = enable, .join_key_pairwise = 1, .join_key_group = 1,
		.native_diag_engaged = !enable,
	};
	int error = old ? -EINVAL : fault ? -EIO : expiry || !remaining ? -ETIMEDOUT : 0;
	clock_ns = 1000000000ULL;
	mac.join_deadline = clock_ns + remaining;
	mac.join_data_deadline = mac.join_deadline;
	/* Let an expired operation enter through disable, not the data-phase gate. */
	if (!remaining)
		assert(!enable);
	calls = 0; fail_at = fault; expire_at = expiry; ended = false;
	memset(emitted, 0, sizeof(emitted));
	mutex_init(&hif.mutex);
	hif.io = (struct mt6797_hif_pio_io) {
		.context = &hif, .write = mt6797_hif_write, .read = mt6797_hif_read,
	};
	assert(!mt6797_normal_admit(&hif.normal, 4, 4, history));
	hif.normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	if (old) {
		assert(mt6797_hif_native_monitor(&hif, 19, enable, 40,
						mac.join_deadline) == error);
	} else {
		mt6797_native_diag_step(&mac);
		assert(mac.sequence == 20 && mac.first_error == error);
		assert(mac.closing == (error != 0));
		assert(mac.join_page_debt == (error ? 0U : 1U));
		assert(mac.join_credit_pending == (error == 0));
		assert(mac.native_diag_engaged == (!enable || !error));
		assert(mac.native_diag_state == (error ? MT6797_ND_CLOSED :
			(enable ? MT6797_ND_ENABLE_PENDING : MT6797_ND_DISABLE_PENDING)));
		assert(hif.deadline_ns == 1000000000ULL +
			(remaining < 100 * NSEC_PER_MSEC ? remaining : 100 * NSEC_PER_MSEC));
	}
	assert(hif.normal.tc4_free == 3 && !hif.mutex.held);
	for (unsigned int i = 0; i < sizeof(history); i++)
		assert(history[i] == (i == 19 / 8 ? (1U << (19 % 8)) : 0));
	assert(calls == (old || !remaining ? 0 : fault ? fault : expiry ? expiry : 7));
	if (error) {
		assert(hif.normal.phase == MT6797_NORMAL_FAILED);
		assert(transaction.phase != MT6797_INIT_IDLE);
		unsigned int before = calls;
		assert(mt6797_hif_native_monitor(&hif, 20, false, 40,
			clock_ns + NSEC_PER_MSEC) == -EIO);
		assert(calls == before && hif.normal.tc4_free == 3);
		assert(!(history[20 / 8] & (1U << (20 % 8))));
	} else {
		assert(hif.normal.phase == MT6797_NORMAL_NVRAM_SUBMITTED);
		assert(transaction.phase == MT6797_INIT_IDLE);
		assert(emitted[0] == 24 && emitted[4] == 0xfc && emitted[7] == 19);
		assert(emitted[8] == enable && emitted[10] == 40);
	}
}
int main(void)
{
	for (unsigned int enable = 0; enable < 2; enable++) {
		exercise(enable, 11184000000ULL, 0, 0, true);
		exercise(enable, 11184000000ULL, 0, 0, false);
		exercise(enable, 10 * NSEC_PER_MSEC, 0, 0, false);
		for (unsigned int fault = 1; fault <= 7; fault++)
			exercise(enable, 11184000000ULL, fault, 0, false);
		exercise(enable, 11184000000ULL, 0, 1, false);
	}
	exercise(false, 0, 0, 0, false);
	return 0;
}
