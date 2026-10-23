/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include "join-pump.h"
#include "pending-source.inc"

int main(void)
{
	unsigned int runs = 0, i, yields = 0, immediate = 0;
	unsigned int queue = 64, owners = 0, turns = 0;

	assert(MT6797_JOIN_PUMP_MAX_ZERO == 32);
	assert(MT6797_JOIN_PUMP_IDLE_MS == 20);
	assert(MT6797_JOIN_PUMP_PENDING_MS == 1);
	for (i = 0; i < 256; i++) {
		assert(mt6797_join_pump_delay(&runs, true, true) == 0);
		assert(!runs);
	}
	for (i = 0; i < 32; i++)
		assert(mt6797_join_pump_delay(&runs, true, false) == 0);
	assert(runs == 32);
	assert(mt6797_join_pump_delay(&runs, true, true) == 0);
	assert(!runs); /* Submission or exact status retirement resets the guard. */
	for (i = 0; i < 10000; i++) {
		unsigned int delay = mt6797_join_pump_delay(&runs, true, false);

		assert(delay == 0 || delay == 1);
		if (delay) {
			assert(immediate == 32 && !runs);
			immediate = 0;
			yields++;
		} else {
			assert(++immediate <= 32);
		}
	}
	assert(yields == 10000 / 33);
	/* All six actual worker pending terms independently prevent idle delay. */
	for (i = 0; i < 64; i++) {
		struct fixture_mac mac = {
			.join_inflight = (i & 2) ? &runs : NULL,
			.data_slots = {.count = !!(i & 4)},
			.join_credit_pending = !!(i & 8),
			.join_page_debt = !!(i & 16),
			.join_data_page_debt = !!(i & 32),
		};
		bool pending = fixture_pending(!!(i & 1), &mac);

		assert(pending == !!i);
		runs = 32;
		assert(mt6797_join_pump_delay(&runs, pending, false) == (i ? 1 : 20));
		assert(!runs);
	}
	/* A finite depth-four burst drains without turning productive passes into
	 * guard backoffs; no-progress pending passes retain the finite guard.
	 */
	while (queue || owners) {
		bool progress = false;
		unsigned int delay;

		if (queue && owners < 4) {
			queue--;
			owners++;
			progress = true;
		}
		if (owners && turns % 3 == 2) {
			owners--;
			progress = true;
		}
		assert(owners <= 4);
		delay = mt6797_join_pump_delay(&runs, queue || owners, progress);
		assert(delay == ((queue || owners) ? 0 : 20));
		assert(++turns < 300);
	}
	assert(!runs && mt6797_join_pump_delay(&runs, false, false) == 20);
	return 0;
}
