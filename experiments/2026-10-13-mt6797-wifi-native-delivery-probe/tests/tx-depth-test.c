/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include "join-depth.h"
#include "pid-source.inc"
#include "room-source.inc"
#include "cleanup-source.inc"
#include "quiescence-source.inc"

int main(void)
{
	struct mt6797_join_pid_pool p = {.next = 1}, saved;
	struct mt6797_data_slots slots = {0}, before;
	int frames[MT6797_DATA_DEPTH + 1];
	unsigned int i;
	unsigned char pid;
	struct mt6797_hif_ledger ledger = {.tc1_free = 1};
	struct mt6797_mac mac = {.hif = &ledger}, mac_before;

	assert(!mt6797_join_pid_take(NULL));
	assert(!mt6797_join_pid_complete(NULL, 1));
	assert(!mt6797_data_put(&slots, 0, frames, 10));
	assert(!mt6797_data_put(&slots, 127, frames, 10));
	assert(!mt6797_data_put(&slots, 1, NULL, 10));
	assert(!slots.count);
	for (i = 0; i < MT6797_DATA_DEPTH; i++) {
		pid = mt6797_join_pid_take(&p);
		assert(pid == i + 1 && pid < 127);
		assert(p.pending == (MT6797_DATA_DEPTH == 1 ? pid : i + 1));
		assert(mt6797_data_put(&slots, pid, &frames[i], 750000000ULL + i));
		assert(mt6797_data_find(&slots, pid)->deadline == 750000000ULL + i);
	}
	assert(slots.count == MT6797_DATA_DEPTH);
	saved = p;
	assert(!mt6797_join_pid_take(&p));
	assert(!memcmp(&p, &saved, sizeof(p)));
	before = slots;
	assert(!mt6797_data_put(&slots, 1, frames, 1));
	assert(!mt6797_data_put(&slots, MT6797_DATA_DEPTH + 1, frames, 1));
	assert(!mt6797_data_room(&slots, 1, 100));
	assert(!memcmp(&slots, &before, sizeof(slots)));
	assert(!fixture_quiescent(&slots, false, 0, NULL));
	assert(!fixture_cleanup_admits(&slots, 0));
	assert(!mt6797_data_expired(&slots, 749999999ULL));
	assert(mt6797_data_expired(&slots, 750000000ULL));
	assert(!memcmp(&slots, &before, sizeof(slots)));
	/* Complete in reverse allocation order, and reject repeated retirement. */
	for (i = MT6797_DATA_DEPTH; i > 0; i--) {
		assert(mt6797_join_pid_complete(&p, i));
		assert(mt6797_data_take(&slots, i) == &frames[i - 1]);
		saved = p;
		assert(!mt6797_join_pid_complete(&p, i));
		assert(!memcmp(&p, &saved, sizeof(p)));
		assert(!mt6797_data_take(&slots, i));
		assert(slots.count == i - 1);
		assert(fixture_quiescent(&slots, false, 0, NULL) == (i == 1));
		assert(fixture_cleanup_admits(&slots, 0) == (i == 1));
	}
	assert(!p.pending && p.allocations == p.completions);
	assert(!fixture_cleanup_admits(&slots, 1));
	assert(fixture_cleanup_admits(&slots, 0));
	assert(!fixture_quiescent(&slots, true, 0, NULL));
	assert(!fixture_quiescent(&slots, false, 1, NULL));
	assert(!fixture_quiescent(&slots, false, 0, frames));
	before = slots;
	assert(!mt6797_data_room(&slots, 0, 100));
	assert(!mt6797_data_room(&slots, 2, 1));
	assert(!mt6797_data_room(&slots, 1, 0));
	assert(mt6797_data_room(&slots, 2, 2));
	assert(!memcmp(&slots, &before, sizeof(slots)));
	mac.ccmp_pid_pool.next = 1;
	mac_before = mac;
	assert(!mt6797_ccmp_data_room(&mac, 200)); /* Two TC1 pages, one free. */
	assert(!memcmp(&mac, &mac_before, sizeof(mac)));
	assert(mt6797_ccmp_data_room(&mac, 100));
	ledger.locked = true;
	assert(!mt6797_ccmp_data_room(&mac, 100));
	ledger.locked = false;
	mac.ccmp_pid_pool.used[1] = true;
	mac.ccmp_pid_pool.completed[1] = false;
	mac_before = mac;
	assert(!mt6797_ccmp_data_room(&mac, 100));
	assert(!memcmp(&mac, &mac_before, sizeof(mac)));
	/* Real round-robin wrap never allocates the reserved PID. */
	for (i = MT6797_DATA_DEPTH + 1; i <= 252; i++) {
		pid = mt6797_join_pid_take(&p);
		assert(pid == (i - 1) % 126 + 1 && pid != 127);
		assert(p.pending == (MT6797_DATA_DEPTH == 1 ? pid : 1));
		assert(mt6797_join_pid_complete(&p, pid));
	}
	assert(p.wraps == 2 && p.next == 1);
	/* A retained busy next PID after wrap refuses without skipping or mutation. */
	p.used[1] = true;
	p.completed[1] = false;
	saved = p;
	assert(!mt6797_join_pid_take(&p));
	assert(!memcmp(&p, &saved, sizeof(p)));
	assert(!mt6797_join_pid_complete(&p, 127));
	assert(mt6797_data_put(&slots, 1, &frames[0], 100));
	assert(mt6797_data_pop(&slots) == &frames[0]);
	assert(!mt6797_data_pop(&slots));
	return 0;
}
