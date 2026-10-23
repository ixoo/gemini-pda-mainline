/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
typedef uint64_t u64;
typedef uint32_t u32;
typedef unsigned char u8;
static char last_log[2048];
static void pr_info(const char *format, ...) __attribute__((format(printf, 1, 2)));
static void pr_info(const char *format, ...)
{
	va_list args;

	va_start(args, format);
	vsnprintf(last_log, sizeof(last_log), format, args);
	va_end(args);
}
#include "lifetime-fence.h"
#include "pn-epoch.h"

static struct mt6797_lifetime_fence_input quiet(void)
{
	return (struct mt6797_lifetime_fence_input) {
		.queue_empty = true, .ledger_whole = true,
		.reply_matched = true, .reply_prefix_proven = true,
		.teardown_completed_ns = 1, .roundtrip_sent_ns = 2,
		.reply_ns = 3, .quiet_start_ns = 4,
		.quiet_end_ns = 4 + MT6797_FENCE_QUIET_NS,
	};
}

static void fence_tests(void)
{
	struct mt6797_lifetime_fence f = {0};
	struct mt6797_lifetime_fence_input i = quiet();

	assert(mt6797_lifetime_drain_fence(&f, &i));
	assert(strstr(last_log, "pass=1 fresh=1 queue_empty=1 ledger_whole=1"));
	assert(strstr(last_log, "admission_unchanged=1"));
	assert(!mt6797_lifetime_drain_fence(&f, &i));
#define REFUSE(field, value) do { \
	f = (struct mt6797_lifetime_fence) {0}; i = quiet(); \
	i.field = (value); \
	assert(!mt6797_lifetime_drain_fence(&f, &i)); \
	assert(strstr(last_log, "pass=0")); \
	i = quiet(); \
	assert(!mt6797_lifetime_drain_fence(&f, &i)); \
} while (0)
	REFUSE(quiet_records, 1);
	assert(strstr(last_log, "fresh=0"));
	REFUSE(card_credit, 1);
	REFUSE(command_credit, 1);
	REFUSE(pending_cpu, 1);
	REFUSE(pending_ffa, 1);
	REFUSE(queue_empty, false);
	REFUSE(pending_records, 1);
	REFUSE(ledger_whole, false);
	REFUSE(reply_matched, false);
	REFUSE(reply_prefix_proven, false);
	REFUSE(teardown_completed_ns, 0);
	REFUSE(roundtrip_sent_ns, 1);
	REFUSE(reply_ns, 1);
	REFUSE(quiet_start_ns, 2);
	REFUSE(quiet_end_ns, 3);
	REFUSE(quiet_end_ns, 4 + MT6797_FENCE_QUIET_NS - 1);
	REFUSE(quiet_end_ns, 4 + MT6797_FENCE_BUDGET_NS + 1);
	f = (struct mt6797_lifetime_fence) {0};
	assert(!mt6797_lifetime_drain_fence(&f, NULL) && f.consumed);
	assert(!mt6797_lifetime_drain_fence(NULL, &i));
#undef REFUSE
}

static void pn_tests(void)
{
	struct mt6797_pn_owner old = {
		.key_identity = 1, .generation = 1, .pairwise = true,
		.peer = {2, 0, 0, 0, 0, 2},
	};
	struct mt6797_pn_owner next = old, mismatch;
	struct mt6797_pn_epoch a = {0}, b = {0}, saved;
	u8 zero[6] = {0}, low[6] = {0, 0, 0, 0, 0, 1};
	u8 high[6] = {0, 0, 0, 0, 0, 100};
	u8 higher[6] = {0, 0, 0, 0, 0, 200};

	assert(!mt6797_pn_epoch_init(&a, &old, NULL));
	assert(mt6797_pn_epoch_init(&a, &old, zero));
	assert(!mt6797_pn_epoch_accept(&a, &old, true, low));
	assert(mt6797_pn_epoch_activate(&a));
	assert(mt6797_pn_epoch_accept(&a, &old, true, high));
	saved = a;
	assert(!mt6797_pn_epoch_accept(&a, &old, true, high));
	assert(!mt6797_pn_epoch_accept(&a, &old, true, low));
	assert(!mt6797_pn_epoch_accept(&a, &old, false, higher));
	assert(!mt6797_pn_epoch_retire(&a, false));
	assert(!memcmp(&a, &saved, sizeof(a)));
	next.key_identity = 2;
	next.generation = 2;
	assert(!mt6797_pn_epoch_init(&a, &next, zero));
	assert(mt6797_pn_epoch_init(&b, &next, zero));
	assert(mt6797_pn_epoch_activate(&b));
	assert(!mt6797_pn_epoch_accept(&b, &old, true, higher));
	assert(!mt6797_pn_epoch_accept(&b, &next, false, higher));
#define MISMATCH(field, value) do { \
	mismatch = next; mismatch.field = (value); saved = b; \
	assert(!mt6797_pn_epoch_accept(&b, &mismatch, true, higher)); \
	assert(!memcmp(&b, &saved, sizeof(b))); \
} while (0)
	MISMATCH(key_identity, 1);
	MISMATCH(generation, 1);
	MISMATCH(key_index, 1);
	MISMATCH(peer[5], 3);
	MISMATCH(pairwise, false);
#undef MISMATCH
	assert(mt6797_pn_epoch_accept(&b, &next, true, low));
	assert(mt6797_pn_epoch_retire(&a, true));
	assert(!memcmp(a.pn, high, sizeof(high)));
	assert(!mt6797_pn_epoch_activate(&a));
	assert(!mt6797_pn_epoch_accept(&a, &old, true, higher));
	assert(!mt6797_pn_epoch_init(&a, &next, zero));
	for (unsigned int key = 0; key < 4; key++) {
		struct mt6797_pn_epoch gtk = {0};

		next.pairwise = false;
		next.key_index = key;
		assert(mt6797_pn_epoch_init(&gtk, &next, NULL));
		assert(!gtk.seeded && !gtk.active);
		assert(!mt6797_pn_epoch_accept(&gtk, &next, true, low));
		assert(mt6797_pn_epoch_activate(&gtk));
		assert(mt6797_pn_epoch_accept(&gtk, &next, true, low));
		assert(gtk.seeded);
		assert(!mt6797_pn_epoch_accept(&gtk, &next, true, low));
		assert(!mt6797_pn_epoch_accept(&gtk, &next, true, zero));
		mismatch = next;
		mismatch.key_index = (key + 1) % 4;
		assert(!mt6797_pn_epoch_accept(&gtk, &mismatch, true, higher));
	}
}

int main(void)
{
	fence_tests();
	pn_tests();
	puts("dormant actual helpers: fence refusals/terminal consumption/logs; PN ownership/activation/fresh-key/strict PN/retirement PASS");
	return 0;
}
