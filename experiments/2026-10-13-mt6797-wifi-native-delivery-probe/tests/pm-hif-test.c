/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <string.h>
#include <stdint.h>
#include <stdio.h>
typedef uint16_t u16;
#include "hif.c"
static unsigned int writes, fail_at, command_word, transfer_bytes;
static u8 *mapping, expected[160];
u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long a, unsigned long b) { (void)a; (void)b; assert(false); }
int mt6797_test_read(void *address, unsigned int *value)
{ (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_write(unsigned int value, void *address)
{
	assert(address == mapping + (writes ? 0x1000 : 0));
	if (!writes) assert(value == command_word);
	else {
		unsigned int n = (writes - 1) * 4;
		assert(n < transfer_bytes);
		assert(value == ((unsigned int)expected[n] | (unsigned int)expected[n + 1] << 8 |
			(unsigned int)expected[n + 2] << 16 | (unsigned int)expected[n + 3] << 24));
	}
	writes++; return writes == fail_at ? -EIO : 0;
}

static void wire(bool abort, unsigned int fault, bool expired, bool held)
{
	struct mt6797_init_transaction transaction = {.phase = MT6797_INIT_IDLE};
	struct mt6797_hif hif = {.transaction = &transaction, .firmware_ready = true, .capability_complete = true};
	struct mt6797_hif_command command;
	unsigned char history[32] = {0};
	unsigned int bytes = abort ? 4 : 12;
	int rc;

	mapping = calloc(1, 0x1004); assert(mapping); hif.base = mapping;
	mutex_init(&hif.mutex);
	hif.io = (struct mt6797_hif_pio_io){.context = &hif, .write = mt6797_hif_write, .read = mt6797_hif_read};
	assert(!mt6797_normal_admit(&hif.normal, 4, 4, history));
	hif.normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
#ifdef TEST_DEAUTH_RETIRE
	if (held) {
		hif.normal.tc4_free--; hif.normal.tc4_pending_ffa = 1;
		assert(abort && mt6797_hif_cleanup_abort_ready(&hif));
	}

#endif
	memset(expected, 0, sizeof(expected));
	expected[0] = 8 + bytes; expected[3] = 0x80; expected[4] = abort ? 0x17 : 0x16;
	expected[5] = 0xa0; expected[6] = 1; expected[7] = 19;
	if (!abort) { expected[9] = 3; expected[10] = 6; expected[12] = 100; }
	assert(!mt6797_hif_encode_command(0x34, MT6797_HIF_WRITE, MT6797_HIF_PIO_ONLY,
		8 + bytes, sizeof(expected), &command));
	command_word = command.word; transfer_bytes = command.transfer_bytes;
	writes = 0; fail_at = fault;
#ifdef TEST_DEAUTH_RETIRE
	if (held) {
		assert(mt6797_hif_join_pm_abort(&hif, 19, 1000000) == -EBUSY && !writes);
		rc = mt6797_hif_join_pm_abort_debt(&hif, 19, 1, expired ? 1000 : 1000000);
	} else
#endif
	rc = abort ? mt6797_hif_join_pm_abort(&hif, 19, expired ? 1000 : 1000000) :
		mt6797_hif_join_pm_connected(&hif, 19, 3, 6, 100, expired ? 1000 : 1000000);
	assert(hif.normal.tc4_free == (held ? 2U : 3U) && history[19 / 8] == (1U << (19 % 8)));
	assert(!hif.mutex.held);
	if (fault || expired) {
		assert(rc < 0 && hif.normal.phase == MT6797_NORMAL_FAILED);
		assert(writes == (expired ? 0 : fault));
	} else {
		assert(!rc && hif.normal.phase == MT6797_NORMAL_NVRAM_SUBMITTED);
		assert(writes == 1 + transfer_bytes / 4);
		writes = 0;
		assert(mt6797_hif_join_pm_abort(&hif, 20, 1000000) == -EBUSY && !writes);
	}
	free(mapping);
}

#ifdef TEST_GTK7
static void gtk7_wire(unsigned int step, unsigned int fault)
{
	struct mt6797_init_transaction transaction = {.phase = MT6797_INIT_IDLE};
	struct mt6797_hif hif = {.transaction = &transaction, .firmware_ready = true, .capability_complete = true};
	unsigned char history[32] = {0};
	struct mt6797_hif_command cmd;
	struct mt6797_normal_release release;
	const unsigned char peer[6] = {2, 0, 0, 0, 0, 2};
	unsigned char off[12] = {0, 0, 0, 1};
	unsigned int bytes = step < 2 ? 64 : step == 2 ? 4 : step == 3 ? 16 : 12;
	unsigned int cid = step < 2 ? 7 : step == 2 ? 0x14 : step == 3 ? 0x1c : MT6797_NORMAL_BSS_ACTIVE;
	unsigned int words[8] = {0};
	int rc;

	mapping = calloc(1, 0x1004); assert(mapping); hif.base = mapping;
	mutex_init(&hif.mutex);
	hif.io = (struct mt6797_hif_pio_io){.context = &hif, .write = mt6797_hif_write, .read = mt6797_hif_read};
	assert(!mt6797_normal_admit(&hif.normal, 4, 4, history));
	hif.normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	hif.normal.tc4_free = 3; hif.normal.tc4_pending_ffa = 1;
	assert(!mt6797_hif_retain_cleanup_page(&hif) && hif.normal.cleanup_retained_pages == 1);
	assert(hif.normal.tc4_free == 3 && hif.normal.tc4_pending_ffa == 1 && mt6797_hif_cleanup_ready(&hif));
	assert(mt6797_hif_retain_cleanup_page(&hif) == -EBUSY);
	memset(expected, 0, sizeof(expected)); expected[0] = 8 + bytes;
	expected[3] = 0x80; expected[4] = cid; expected[5] = 0xa0; expected[6] = 1; expected[7] = 41;
	if (step == 0) { expected[10] = 1; memcpy(expected + 12, peer, 6); expected[22] = 1; }
	if (step == 1) { expected[20] = 1; expected[22] = MT6797_JOIN_RESERVED_WLAN_INDEX; }
	if (step == 2) expected[9] = 1;
	if (step == 3) { expected[9] = 1; expected[10] = 1; }
	if (step == 4) expected[11] = 1;
	assert(!mt6797_hif_encode_command(0x34, MT6797_HIF_WRITE, MT6797_HIF_PIO_ONLY, 8 + bytes, sizeof(expected), &cmd));
	command_word = cmd.word; transfer_bytes = cmd.transfer_bytes; writes = 0; fail_at = fault;
	if (step < 2) rc = mt6797_hif_join_key(&hif, 41, false, step == 0, step == 0 ? peer : NULL, step == 0 ? 0 : 1, NULL, 1000000);
	else if (step == 2) rc = mt6797_hif_join_remove_station(&hif, 41, 1000000);
	else if (step == 3) rc = mt6797_hif_join_channel(&hif, 41, 1, 40, 0, true, 1000000);
	else rc = mt6797_hif_send_config(&hif, MT6797_NORMAL_BSS_ACTIVE, 41, off, sizeof(off), 1000000);
	if (hif.mutex.held || hif.normal.tc4_free != 2 || hif.normal.cleanup_retained_pages != 1)
		fprintf(stderr, "step=%u fault=%u rc=%d writes=%u free=%u retained=%u phase=%u\n", step, fault, rc, writes, hif.normal.tc4_free, hif.normal.cleanup_retained_pages, hif.normal.phase);
	assert(!hif.mutex.held && hif.normal.tc4_free == 2 && hif.normal.cleanup_retained_pages == 1);
	if (fault) {
		assert(rc < 0 && writes == fault && hif.normal.phase == MT6797_NORMAL_FAILED);
		assert(!mt6797_hif_cleanup_ready(&hif));
	} else {
		assert(!rc && writes == 1 + transfer_bytes / 4 && !mt6797_hif_cleanup_ready(&hif));
		words[7] = (1U << 16) | 1;
		assert(!mt6797_normal_reconcile(&hif.normal, words, &release));
		assert(release.released_pages == 1 && hif.normal.tc4_free == 3 && hif.normal.tc4_pending_ffa == 1);
		assert(mt6797_hif_cleanup_ready(&hif));
	}
	free(mapping);
}
#endif

int main(void)
{
	for (unsigned int abort = 0; abort <= 1; abort++) {
		unsigned int words = abort ? 4 : 6;
		wire(abort, 0, false, false); wire(abort, 0, true, false);
		for (unsigned int fault = 1; fault <= words; fault++) wire(abort, fault, false, false);
	}
#ifdef TEST_DEAUTH_RETIRE
	wire(true, 0, false, true); wire(true, 0, true, true);
	for (unsigned int fault = 1; fault <= 4; fault++) wire(true, fault, false, true);
#endif
#ifdef TEST_GTK7
	for (unsigned int step = 0; step < 5; step++) {
		gtk7_wire(step, 0);
		unsigned int words = 1 + ((step < 2 ? 72 : step == 2 ? 12 : step == 3 ? 24 : 20) / 4);
		for (unsigned int fault = 1; fault <= words; fault++) gtk7_wire(step, fault);
	}
	puts("GTK7 actual HIF: PASS retained page across key/STA/channel/BSS-off wire encodings and every transfer cut, no refund; host I/O shim only");
#endif
	puts("PM actual HIF: PASS exact 0x16/0x17 wire, sequence/page debt, all write cuts/expiry/no refund; guard-disabled host I/O shim only");
	return 0;
}
