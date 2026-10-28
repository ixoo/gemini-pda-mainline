/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include "join-rearm.h"

/* Exercises the re-arm decision (proposal 0180, later 0240, 0334): the
 * rendezvous in both orders, the quiescent gate, the poison short-circuit,
 * the wire-identity wrap and the command-sequence recycle. The two-lifetime
 * cap (0240) and the PID wrap (cyclic PID) are gone. No kernel, synthetic.
 */
static struct mt6797_join_rearm_state healthy(void)
{
	/* A lifetime 1 that reached its healthy terminal, both facts observed. */
	struct mt6797_join_rearm_state s = {0};

	s.cleanup_done = true;
	s.sta_removed = true;
	s.poisoned = false;
	s.key_done = true;
	s.key_done_second = true;
	s.inflight = false;
	s.credit_pending = false;
	s.queue_empty = true;
	s.key_pairwise = 2;
	s.key_group = 2;
	s.page_debt = 0;
	s.data_page_debt = 0;
	s.lifetimes = 1;
	s.channel_token = 1;
	s.sta_sequence = 1;
	s.sequence = 30;
	s.sequence_base = 10;
	s.next_pid = 33;  /* lifetime 1 consumed ~32 pids; room remains */
	return s;
}

int main(void)
{
	struct mt6797_join_rearm_state s;

	/* Rendezvous, both orders: neither fact alone re-arms; both do. */
	s = healthy(); s.cleanup_done = true; s.sta_removed = false;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO); /* cleanup first, teardown pending */
	s = healthy(); s.cleanup_done = false; s.sta_removed = true;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO); /* teardown first, cleanup pending */
	s = healthy();
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_YES); /* both observed */

	/* Poison is never re-armed, whatever the rendezvous/gate. */
	s = healthy(); s.poisoned = true;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);

	/* No lifetime cap: the eleventh re-arms like the first. */
	s = healthy(); s.lifetimes = 11; s.sequence = 196;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_YES);

	/* Each quiescent/obligation gate blocks re-arm individually. */
	s = healthy(); s.key_pairwise = 1; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.key_group = 1;    assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.key_done = false; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.key_done_second = false; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.inflight = true;  assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.page_debt = 1;    assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.data_page_debt = 1; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.credit_pending = true; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.queue_empty = false; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);

	/* A u8 wire-identity wrap refuses (the caller poisons). */
	s = healthy(); s.channel_token = 255; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	s = healthy(); s.sta_sequence = 255;  assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	s = healthy(); s.next_pid = 64;       assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_YES); /* the PID is cyclic */
	/* The command sequence recycles to the base once two lifetimes no longer
	 * fit (22 commands each), and only with a valid base; else the old wrap.
	 */
	s = healthy(); s.sequence = 200;      assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_YES);
	s = healthy(); s.sequence = 201;      assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_RECYCLE);
	s = healthy(); s.sequence = 252;      assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_RECYCLE);
	s = healthy(); s.sequence = 230; s.sequence_base = 0;   assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_YES);
	s = healthy(); s.sequence = 249; s.sequence_base = 0;   assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	s = healthy(); s.sequence = 249; s.sequence_base = 129; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	s = healthy(); s.sequence = 252; s.channel_token = 255; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	/* Recycle, like wrap, is decided only once the rendezvous and gate pass. */
	s = healthy(); s.sequence = 240; s.credit_pending = true;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	/* Wrap is only decided once the rendezvous and gate otherwise pass. */
	s = healthy(); s.channel_token = 255; s.sta_removed = false;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);

	puts("join-rearm: PASS (rendezvous both orders; no cap; poison; each gate; token/sta wrap; sequence recycle)");
	return 0;
}
