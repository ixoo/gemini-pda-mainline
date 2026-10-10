/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "join-submit.h"
#include "join-command-submit.h"

/* Phase C3 transmit: the protected data descriptor (TC1 queue bits, Ethernet
 * II format, protected bit, TID 0, fixed rate, PID with TX status), the data
 * preparation on the admitted TC1 pool (one frame in flight, pool whole), and
 * the ledger reconciliation with AC1 and free-for-all counts shared with TC4:
 * fulfilled pools, scarce pool (TC4 first, remainder pending), foreign queue
 * counts and overflows refused. Synthetic bytes only.
 */
static void ready(struct mt6797_normal_transaction *t, unsigned char *history)
{
	*t = (struct mt6797_normal_transaction){0};
	assert(!mt6797_normal_admit(t, 26, 26, history));
	assert(!mt6797_normal_admit_tc1(t, 16, 16));
	t->phase = MT6797_NORMAL_NVRAM_SUBMITTED;
}

int main(void)
{
	static const unsigned char own[6] = {2, 0, 0, 0, 0, 1}, ap[6] = {2, 0, 0, 0, 0, 2};
	static const unsigned char bcast[6] = {255, 255, 255, 255, 255, 255};
	unsigned char frame[1518], d[MT6797_JOIN_TX_DESC_BYTES], history[32] = {0}, out[2560];
	struct mt6797_normal_transaction t;
	struct mt6797_hif_command command;
	struct mt6797_normal_release release;
	unsigned int pages, words[8], i;

	memset(frame, 0x5a, sizeof(frame));
	memcpy(frame, ap, 6); memcpy(frame + 6, own, 6); frame[12] = 0x08; frame[13] = 0x00;
	/* Descriptor for a 342-byte frame: 3 pages, TC1 queue bits, protected, TID 0. */
	assert(mt6797_join_tx_data_descriptor(frame, 342, 1, 9, 500, 3, d, &pages));
	assert(pages == (28 + 342 + 127) / 128 && d[0] == (unsigned char)(28 + 342) && d[1] == (28 + 342) >> 8);
	assert(d[2] == 20 && d[3] == 0x08 && d[4] == 1 && d[5] == 0x90 && d[6] == 0x80 && d[7] == 4);
	assert(d[10] == 15 && d[11] == 0x80 && d[12] == 0x00 && d[13] == 0x18 && d[20] == 9 && d[21] == 2);
	assert(d[26] == (unsigned char)(0x4b << 2) && d[27] == (0x4b << 2) >> 8);
	for (i = 14; i < 20; i++) assert(!d[i]);
	for (i = 22; i < 26; i++) assert(!d[i]);
	assert(!d[8] && !d[9]);
	/* Group destinations (ARP, DHCP) are admitted; a group source, EAPOL type,
	 * bounds and arguments are refused. */
	memcpy(frame, bcast, 6); assert(mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 500, 3, d, &pages) && pages == 1);
	frame[6] |= 1; assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 500, 3, d, &pages)); frame[6] &= ~1;
	frame[12] = 0x88; frame[13] = 0x8e; assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 500, 3, d, &pages));
	frame[12] = 0x08; frame[13] = 0x00;
	assert(!mt6797_join_tx_data_descriptor(frame, 13, 1, 9, 500, 3, d, &pages));
	assert(mt6797_join_tx_data_descriptor(frame, 14, 1, 9, 500, 3, d, &pages));
	assert(mt6797_join_tx_data_descriptor(frame, 1518, 1, 9, 500, 3, d, &pages) && pages == 13);
	assert(!mt6797_join_tx_data_descriptor(frame, 1519, 1, 9, 500, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 31, 9, 500, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 0, 500, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 128, 500, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 0, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 10001, 3, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 500, 0, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(frame, 60, 1, 9, 500, 31, d, &pages));
	assert(!mt6797_join_tx_data_descriptor(NULL, 60, 1, 9, 500, 3, d, &pages));
	/* Pool admission: once, after TC4, bounded. */
	ready(&t, history);
	assert(mt6797_normal_admit_tc1(&t, 16, 16) < 0); /* twice */
	ready(&t, history);
	{ struct mt6797_normal_transaction u = {0}, v = {0};
	  assert(mt6797_normal_admit_tc1(&u, 16, 16) < 0 && u.phase == MT6797_NORMAL_FAILED); /* before TC4: fail closed */
	  assert(!mt6797_normal_admit(&v, 26, 26, history));
	  assert(mt6797_normal_admit_tc1(&v, 0, 0) == -EINVAL && mt6797_normal_admit_tc1(&v, 16, 17) == -EINVAL);
	  assert(mt6797_normal_admit_tc1(&v, 0x10000, 1) == -EINVAL && v.phase == MT6797_NORMAL_IDLE && !v.tc1_limit); }
	/* Preparation debits the TC1 pool only; TC4 stays whole; one in flight. */
	memset(out, 0xa5, sizeof(out));
	assert(!mt6797_join_prepare_data(&t, frame, 342, 1, 9, 500, 3, out, sizeof(out), &command));
	assert(t.tc1_free == 13 && t.tc4_free == 26 && t.phase == MT6797_NORMAL_CONFIG_TX);
	assert(out[3] == 0x08 && out[6] == 0x80 && !memcmp(out + 28, frame, 342));
	for (i = 28 + 342; i < command.transfer_bytes; i++) assert(!out[i]);
	assert(!mt6797_normal_submitted(&t, 0) && t.phase == MT6797_NORMAL_NVRAM_SUBMITTED);
	assert(mt6797_join_prepare_data(&t, frame, 60, 1, 10, 500, 3, out, sizeof(out), &command) == -EBUSY);
	/* A TC4 command may still go while data pages are owed: separate pools. */
	{ unsigned char payload[4] = {9, 0, 0, 0};
	  assert(!mt6797_join_prepare_command(&t, 0x0a, 7, payload, 4, out, sizeof(out), &command));
	  assert(t.tc4_free == 25 && !mt6797_normal_submitted(&t, 0)); }
	/* Reconciliation: AC1 count in word 0's high half with the pool: data pages
	 * return; the TC4 page returns by CPU count with the pool. Foreign queue
	 * counts (AC0 low half, words 1..6) are refused; overflows are refused. */
	memset(words, 0, sizeof(words));
	words[0] = 3U << 16; words[7] = 0; /* AC1 done, no pool yet: pending */
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.tc1_released == 0 && release.pending_ac1 == 3 && t.tc1_free == 13 && !release.released_pages);
	words[0] = 0; words[7] = (1U << 16) | 4; /* CPU 1 and pool 4: TC4 first (1), then TC1 (3) */
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.released_pages == 1 && t.tc4_free == 26 && release.tc1_released == 3 && t.tc1_free == 16);
	assert(!release.pending_ac1 && !release.pending_cpu && !release.pending_ffa);
	/* Scarce pool: TC4 first, the TC1 remainder stays pending; the next snapshot completes it. */
	assert(!mt6797_join_prepare_data(&t, frame, 342, 1, 11, 500, 3, out, sizeof(out), &command) && !mt6797_normal_submitted(&t, 0));
	{ unsigned char payload[4] = {9, 0, 0, 0};
	  assert(!mt6797_join_prepare_command(&t, 0x0a, 8, payload, 4, out, sizeof(out), &command) && !mt6797_normal_submitted(&t, 0)); }
	memset(words, 0, sizeof(words)); words[0] = 3U << 16; words[7] = (1U << 16) | 2;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.released_pages == 1 && release.tc1_released == 1 && release.pending_ac1 == 2 && t.tc1_free == 14 && !release.pending_ffa);
	memset(words, 0, sizeof(words)); words[7] = 2;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.tc1_released == 2 && t.tc1_free == 16 && !release.pending_ac1);
	/* Pool-first: TC4 whole, TC1 owing 3; a snapshot with the pool count alone leaves
	 * it pending (bounded by both debts, not TC4's), and the AC1 count that follows
	 * releases the three pages. Then a split: AC1 3 with pool 1, the rest later. */
	assert(!mt6797_join_prepare_data(&t, frame, 342, 1, 13, 500, 3, out, sizeof(out), &command) && !mt6797_normal_submitted(&t, 0));
	assert(t.tc4_free == 26 && t.tc1_free == 13);
	memset(words, 0, sizeof(words)); words[7] = 3;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(!release.tc1_released && release.pending_ffa == 3 && !release.pending_ac1 && t.tc1_free == 13);
	memset(words, 0, sizeof(words)); words[0] = 3U << 16;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.tc1_released == 3 && t.tc1_free == 16 && !release.pending_ffa && !release.pending_ac1);
	assert(!mt6797_join_prepare_data(&t, frame, 342, 1, 14, 500, 3, out, sizeof(out), &command) && !mt6797_normal_submitted(&t, 0));
	memset(words, 0, sizeof(words)); words[0] = 3U << 16; words[7] = 1;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.tc1_released == 1 && release.pending_ac1 == 2 && !release.pending_ffa && t.tc1_free == 14);
	memset(words, 0, sizeof(words)); words[7] = 2;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.tc1_released == 2 && !release.pending_ac1 && t.tc1_free == 16);
	/* Both pools owing with one snapshot covering both: TC4 first, then TC1. */
	assert(!mt6797_join_prepare_data(&t, frame, 342, 1, 15, 500, 3, out, sizeof(out), &command) && !mt6797_normal_submitted(&t, 0));
	{ unsigned char payload[4] = {9, 0, 0, 0};
	  assert(!mt6797_join_prepare_command(&t, 0x0a, 9, payload, 4, out, sizeof(out), &command) && !mt6797_normal_submitted(&t, 0)); }
	memset(words, 0, sizeof(words)); words[0] = 3U << 16; words[7] = (1U << 16) | 4;
	assert(!mt6797_normal_reconcile(&t, words, &release));
	assert(release.released_pages == 1 && release.tc1_released == 3 && t.tc4_free == 26 && t.tc1_free == 16 && !release.pending_ffa);
	/* Orphan TC1 count: an AC1 count with no TC1 debt aborts the ledger. */
	{ struct mt6797_normal_transaction saved = t;
	  memset(words, 0, sizeof(words)); words[0] = 1U << 16; assert(mt6797_normal_reconcile(&t, words, &release) < 0); t = saved; }
	/* Refusals leave the ledger aborted: AC0 count, another queue, AC1 above the debt, pool above both debts. */
	{ struct mt6797_normal_transaction saved = t;
	  memset(words, 0, sizeof(words)); words[0] = 1; assert(mt6797_normal_reconcile(&t, words, &release) < 0); t = saved;
	  memset(words, 0, sizeof(words)); words[3] = 1; assert(mt6797_normal_reconcile(&t, words, &release) < 0); t = saved;
	  memset(words, 0, sizeof(words)); words[0] = 1U << 16; assert(mt6797_normal_reconcile(&t, words, &release) < 0); t = saved;
	  memset(words, 0, sizeof(words)); words[7] = 1; assert(mt6797_normal_reconcile(&t, words, &release) < 0); t = saved; }
	/* Without an admitted pool the TC4-only ledger behaves as before and refuses data. */
	{ struct mt6797_normal_transaction u = {0};
	  assert(!mt6797_normal_admit(&u, 26, 26, history)); u.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
	  memset(words, 0, sizeof(words)); assert(!mt6797_normal_reconcile(&u, words, &release) && !release.tc1_released);
	  { struct mt6797_normal_transaction saved = u;
	    memset(words, 0, sizeof(words)); words[0] = 1U << 16; assert(mt6797_normal_reconcile(&u, words, &release) < 0); u = saved; }
	  /* A data frame without an admitted pool aborts the ledger, fail closed. */
	  assert(mt6797_join_prepare_data(&u, frame, 60, 1, 12, 500, 3, out, sizeof(out), &command) < 0 && u.phase == MT6797_NORMAL_FAILED); }
	puts("data-tx: PASS (TC1 descriptor, pool admission and debit, AC1/FFA reconciliation with TC4, refusals)");
	return 0;
}
