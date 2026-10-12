/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include "join-rearm.h"

/* Exercises the bounded two-lifetime re-arm decision (proposal 0180): the
 * rendezvous in both orders, the quiescent gate, the two-lifetime cap, the
 * poison short-circuit and the wire-identity wrap. No kernel, synthetic only.
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
	s.key_pairwise = 2;
	s.key_group = 2;
	s.page_debt = 0;
	s.data_page_debt = 0;
	s.lifetimes = 1;
	s.channel_token = 1;
	s.sta_sequence = 1;
	s.sequence = 30;
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

	/* Two-lifetime cap: a third is refused. */
	s = healthy(); s.lifetimes = 2;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);

	/* Each quiescent/obligation gate blocks re-arm individually. */
	s = healthy(); s.key_pairwise = 1; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.key_group = 1;    assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.key_done = false; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.key_done_second = false; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.inflight = true;  assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.page_debt = 1;    assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.data_page_debt = 1; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);
	s = healthy(); s.credit_pending = true; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);

	/* A u8 wire-identity wrap or an exhausted command sequence refuses
	 * (the caller poisons) rather than reuse a value.
	 */
	s = healthy(); s.channel_token = 255; assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	s = healthy(); s.sta_sequence = 255;  assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	s = healthy(); s.sequence = 249;      assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_WRAP);
	/* Wrap is only decided once the rendezvous and gate otherwise pass. */
	s = healthy(); s.channel_token = 255; s.sta_removed = false;
	assert(mt6797_join_rearm_ready(&s) == MT6797_JOIN_REARM_NO);

	puts("join-rearm: PASS (rendezvous both orders; cap; poison; each gate; token/sta/sequence wrap)");
	return 0;
}
