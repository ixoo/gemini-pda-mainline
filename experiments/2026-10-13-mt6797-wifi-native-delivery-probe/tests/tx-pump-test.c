/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include "join-pump.h"

int main(void)
{
	unsigned int runs = 0, i, backoffs = 0;

	assert(mt6797_join_pump_delay(&runs, false) == 20);
	assert(!runs);
	assert(mt6797_join_pump_delay(&runs, true) == 0);
	assert(runs == 1);
	assert(mt6797_join_pump_delay(&runs, false) == 20);
	assert(!runs);
	for (i = 0; i < MT6797_JOIN_PUMP_MAX_ZERO; i++)
		assert(mt6797_join_pump_delay(&runs, true) == 0);
	assert(mt6797_join_pump_delay(&runs, true) == 20);
	assert(!runs);
	for (i = 0; i < 10000; i++) {
		if (mt6797_join_pump_delay(&runs, true) == 20)
			backoffs++;
		assert(runs <= MT6797_JOIN_PUMP_MAX_ZERO);
	}
	assert(backoffs == 10000 / (MT6797_JOIN_PUMP_MAX_ZERO + 1));
	return 0;
}
