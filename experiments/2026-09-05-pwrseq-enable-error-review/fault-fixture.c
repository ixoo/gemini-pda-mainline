// SPDX-License-Identifier: GPL-2.0-only
/* Host control-flow fixture; Linux function is inserted from pinned source. */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

struct device { bool registered; };
struct pwrseq_device { struct device dev; int rw_lock, state_lock; };
struct pwrseq_unit { int unused; };
struct pwrseq_target {
	struct pwrseq_unit *unit;
	int (*post_enable)(struct pwrseq_device *);
};
struct pwrseq_desc {
	struct pwrseq_device *pwrseq;
	struct pwrseq_target *target;
	bool powered_on;
};
struct hold { int *lock; bool active; };
static struct hold acquire(int *lock)
{
	if ((*lock)++) abort();
	return (struct hold){lock, true};
}
static void release(struct hold *hold)
{
	if (hold->active) { --*hold->lock; hold->active = false; }
}
#define guard(kind) struct hold outer __attribute__((cleanup(release))) = acquire
#define scoped_guard(kind, lock) \
	for (struct hold inner __attribute__((cleanup(release))) = acquire(lock); \
	     inner.active; release(&inner))
#define might_sleep() ((void)0)
static bool device_is_registered(struct device *dev) { return dev->registered; }
static int unit_ret, post_ret, disable_ret, enabled, posted, disabled;
static int pwrseq_unit_enable(struct pwrseq_device *p, struct pwrseq_unit *u)
{
	(void)u;
	if (p->rw_lock != 1 || p->state_lock != 1) abort();
	++enabled;
	return unit_ret;
}
static int pwrseq_unit_disable(struct pwrseq_device *p, struct pwrseq_unit *u)
{
	(void)u;
	if (p->rw_lock != 1 || p->state_lock != 1) abort();
	++disabled;
	return disable_ret;
}
static int post_enable(struct pwrseq_device *p)
{
	if (p->rw_lock != 1 || p->state_lock != 0) abort();
	++posted;
	return post_ret;
}
/* ACTUAL_FUNCTION */
struct test_case {
	const char *name;
	bool null_desc, on, registered, callback;
	int unit_error, post_error, disable_error;
	int result, enable_calls, post_calls, disable_calls;
	bool final_on;
};
int main(void)
{
	const struct test_case cases[] = {
		{"null", true, false, true, true, 0, 0, 0, 0, 0, 0, 0, false},
		{"already-on", false, true, true, true, 0, 0, 0, 0, 0, 0, 0, true},
		{"unregistered", false, false, false, true, 0, 0, 0, -ENODEV, 0, 0, 0, false},
		{"unit-fail-no-post", false, false, true, false, -EIO, 0, 0, -EIO, 1, 0, 0, false},
		{"unit-fail-post-success", false, false, true, true, -EIO, 0, 0, -EIO, 1, 0, 0, false},
		{"unit-fail-post-error", false, false, true, true, -EIO, -EINVAL, 0, -EIO, 1, 0, 0, false},
		{"success-no-post", false, false, true, false, 0, 0, 0, 0, 1, 0, 0, true},
		{"success-post", false, false, true, true, 0, 0, 0, 0, 1, 1, 0, true},
		{"post-failure", false, false, true, true, 0, -EINVAL, 0, -EINVAL, 1, 1, 1, false},
		{"post-and-rollback-failure", false, false, true, true, 0, -EINVAL, -EBUSY, -EINVAL, 1, 1, 1, false},
	};
	int failures = 0;
	for (unsigned int i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
		const struct test_case *c = &cases[i];
		struct pwrseq_device p = {.dev.registered = c->registered};
		struct pwrseq_unit unit = {0};
		struct pwrseq_target target = {&unit, c->callback ? post_enable : NULL};
		struct pwrseq_desc desc = {&p, &target, c->on};
		unit_ret = c->unit_error; post_ret = c->post_error; disable_ret = c->disable_error;
		enabled = posted = disabled = 0;
		int ret = pwrseq_enable(c->null_desc ? NULL : &desc);
		bool pass = ret == c->result && enabled == c->enable_calls &&
			posted == c->post_calls && disabled == c->disable_calls &&
			desc.powered_on == c->final_on && !p.rw_lock && !p.state_lock;
		printf("%s=%s\n", c->name, pass ? "pass" : "fail");
		failures += !pass;
	}
	return failures ? 1 : 0;
}
