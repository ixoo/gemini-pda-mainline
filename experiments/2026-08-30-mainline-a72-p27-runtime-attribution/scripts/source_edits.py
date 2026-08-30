#!/usr/bin/env python3
"""Pure source edits for read-only CPU8 P27 runtime attribution."""

from __future__ import annotations

from pathlib import Path


BINDER_HEADER = Path("include/linux/soc/mediatek/mt6797-a72-binder.h")
BINDER_INTERNAL = Path("drivers/soc/mediatek/mt6797-a72-binder-internal.h")
BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
CONTROLLER = Path("drivers/soc/mediatek/mt6797-a72-admission-controller.c")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source match, found {count}")
    return text.replace(old, new, 1)


def apply_header(root: Path) -> None:
    path = root / BINDER_HEADER
    text = path.read_text(encoding="utf-8")
    anchor = "typedef int (*mt6797_a72_cpu_boot_fn)(unsigned int cpu);\n"
    definition = r'''typedef int (*mt6797_a72_cpu_boot_fn)(unsigned int cpu);

#define MT6797_A72_BINDER_DIAGNOSTIC_ABI 1U

struct mt6797_a72_binder_diagnostic {
	u32 abi;
	u32 lifecycle;
	u32 terminal;
	u32 last_stage;
	s32 stage_errno;
	s32 rollback_errno;
	s32 checkpoint_errno;
	u32 attempted;
	u32 watchdog_armed;
	u32 p27_owned;
	u32 rollback_mask;
	u32 retained_mask;
	u32 p27_acquire_operation;
	s32 p27_acquire_error;
	u32 p27_acquire_attempted;
	u32 p27_acquire_completed;
	u32 p27_acquire_spm_before;
	u32 p27_acquire_spm_after;
	u32 p27_acquire_bpll;
	u32 p27_acquire_owned;
	u32 p27_acquire_sealed;
	u32 p27_release_operation;
	s32 p27_release_error;
	u32 p27_release_attempted;
	u32 p27_release_completed;
	u32 p27_release_spm_before;
	u32 p27_release_spm_after;
	u32 p27_release_bpll;
	u32 p27_release_owned;
	u32 p27_release_sealed;
};
'''
    text = replace_once(text, anchor, definition, "public diagnostic definition")
    prototype = r'''bool mt6797_a72_binder_available(void);
int
mt6797_a72_binder_diagnostic_snapshot(struct mt6797_a72_binder_diagnostic *snapshot);
'''
    text = replace_once(
        text,
        "bool mt6797_a72_binder_available(void);\n",
        prototype,
        "public diagnostic prototype",
    )
    stub_anchor = r'''static inline bool mt6797_a72_binder_available(void)
{
	return false;
}

'''
    stub = stub_anchor + r'''static inline int
mt6797_a72_binder_diagnostic_snapshot(struct mt6797_a72_binder_diagnostic *snapshot)
{
	if (snapshot)
		*snapshot = (struct mt6797_a72_binder_diagnostic){};
	return -EOPNOTSUPP;
}

'''
    text = replace_once(text, stub_anchor, stub, "disabled diagnostic stub")
    path.write_text(text, encoding="utf-8")


def apply_internal(root: Path) -> None:
    path = root / BINDER_INTERNAL
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "\tstruct mt6797_a72_platform_effect_result p27;\n",
        "\tstruct mt6797_a72_platform_effect_result p27;\n"
        "\tstruct mt6797_a72_platform_effect_result p27_release;\n",
        "retained P27 release result",
    )
    prototype = r'''void mt6797_a72_binder_test_init(struct mt6797_a72_binder *binder,
				 const struct mt6797_a72_binder_backend_ops *backend);
void
mt6797_a72_binder_test_diagnostic(const struct mt6797_a72_binder *binder,
				   struct mt6797_a72_binder_diagnostic *snapshot);
'''
    original = r'''void mt6797_a72_binder_test_init(struct mt6797_a72_binder *binder,
				 const struct mt6797_a72_binder_backend_ops *backend);
'''
    text = replace_once(text, original, prototype, "KUnit diagnostic prototype")
    path.write_text(text, encoding="utf-8")


def apply_binder(root: Path) -> None:
    path = root / BINDER
    text = path.read_text(encoding="utf-8")
    available = r'''bool mt6797_a72_binder_available(void)
{
	bool available;

	mutex_lock(&mt6797_a72_binder_publish_lock);
	available = !!mt6797_a72_binder_ready();
	mutex_unlock(&mt6797_a72_binder_publish_lock);
	return available;
}
'''
    diagnostic = available + r'''
static void
mt6797_a72_binder_fill_diagnostic(const struct mt6797_a72_binder *binder,
				   struct mt6797_a72_binder_diagnostic *snapshot)
{
	const struct mt6797_a72_platform_effect_result *acquire = &binder->p27;
	const struct mt6797_a72_platform_effect_result *release =
		&binder->p27_release;

	memset(snapshot, 0, sizeof(*snapshot));
	snapshot->abi = MT6797_A72_BINDER_DIAGNOSTIC_ABI;
	snapshot->lifecycle = atomic_read_acquire(&binder->transition.lifecycle);
	snapshot->terminal = binder->result.terminal;
	snapshot->last_stage = binder->result.last_stage;
	snapshot->stage_errno = binder->result.stage_errno;
	snapshot->rollback_errno = binder->result.rollback_errno;
	snapshot->checkpoint_errno = binder->result.checkpoint_errno;
	snapshot->attempted = binder->result.attempted;
	snapshot->watchdog_armed = binder->result.watchdog_armed;
	snapshot->p27_owned = binder->result.p27_owned;
	snapshot->rollback_mask = binder->result.rollback_mask;
	snapshot->retained_mask = binder->result.retained_mask;
	snapshot->p27_acquire_operation = acquire->operation;
	snapshot->p27_acquire_error = acquire->error;
	snapshot->p27_acquire_attempted = acquire->attempted_effects;
	snapshot->p27_acquire_completed = acquire->completed_effects;
	snapshot->p27_acquire_spm_before = acquire->spm_p27_before;
	snapshot->p27_acquire_spm_after = acquire->spm_p27_after;
	snapshot->p27_acquire_bpll = acquire->bpll_ordering_value;
	snapshot->p27_acquire_owned = acquire->p27_owned;
	snapshot->p27_acquire_sealed = acquire->sealed;
	snapshot->p27_release_operation = release->operation;
	snapshot->p27_release_error = release->error;
	snapshot->p27_release_attempted = release->attempted_effects;
	snapshot->p27_release_completed = release->completed_effects;
	snapshot->p27_release_spm_before = release->spm_p27_before;
	snapshot->p27_release_spm_after = release->spm_p27_after;
	snapshot->p27_release_bpll = release->bpll_ordering_value;
	snapshot->p27_release_owned = release->p27_owned;
	snapshot->p27_release_sealed = release->sealed;
}

int
mt6797_a72_binder_diagnostic_snapshot(struct mt6797_a72_binder_diagnostic *snapshot)
{
	struct mt6797_a72_binder *binder;
	int ret = 0;

	if (!snapshot)
		return -EINVAL;
	memset(snapshot, 0, sizeof(*snapshot));
	mutex_lock(&mt6797_a72_binder_publish_lock);
	binder = mt6797_a72_binder_ready();
	if (binder)
		mt6797_a72_binder_fill_diagnostic(binder, snapshot);
	else
		ret = -EAGAIN;
	mutex_unlock(&mt6797_a72_binder_publish_lock);
	return ret;
}
'''
    text = replace_once(text, available, diagnostic, "diagnostic implementation")

    old_release = r'''static int mt6797_a72_binder_p27_release(void *context)
{
	struct mt6797_a72_binder *binder = context;
	struct mt6797_a72_p29_rollback_proof rollback = { };
	struct mt6797_a72_platform_effect_result result = { };
	int ret;

	ret = binder->backend->p27_release(binder->platform_state,
					   &binder->effect_handle, &result);
	if (ret)
		return ret;
	if (!mt6797_a72_effect_result_shape(&result,
					    MT6797_A72_PLATFORM_EFFECT_P27_RELEASE) ||
	    result.error || result.p27_owned ||
	    result.attempted_effects != MT6797_A72_BINDER_P27_RELEASE_COMPLETE ||
	    result.completed_effects != MT6797_A72_BINDER_P27_RELEASE_COMPLETE)
		return -EPROTO;
'''
    new_release = r'''static int mt6797_a72_binder_p27_release(void *context)
{
	struct mt6797_a72_binder *binder = context;
	struct mt6797_a72_p29_rollback_proof rollback = { };
	int ret;

	memset(&binder->p27_release, 0, sizeof(binder->p27_release));
	ret = binder->backend->p27_release(binder->platform_state,
					   &binder->effect_handle,
					   &binder->p27_release);
	if (ret)
		return ret;
	if (!mt6797_a72_effect_result_shape(&binder->p27_release,
					    MT6797_A72_PLATFORM_EFFECT_P27_RELEASE) ||
	    binder->p27_release.error || binder->p27_release.p27_owned ||
	    binder->p27_release.attempted_effects !=
		    MT6797_A72_BINDER_P27_RELEASE_COMPLETE ||
	    binder->p27_release.completed_effects !=
		    MT6797_A72_BINDER_P27_RELEASE_COMPLETE)
		return -EPROTO;
'''
    text = replace_once(text, old_release, new_release, "retained P27 release")

    test_init = r'''void mt6797_a72_binder_test_init(struct mt6797_a72_binder *binder,
				 const struct mt6797_a72_binder_backend_ops *backend)
{
	memset(binder, 0, sizeof(*binder));
	binder->backend = backend;
	atomic_set(&binder->transition.consumed, 0);
	atomic_set(&binder->transition.lifecycle,
		   MT6797_A72_TRANSITION_LIFECYCLE_IDLE);
	atomic_set(&binder->boot_claimed, 0);
}
'''
    test_diagnostic = test_init + r'''
void
mt6797_a72_binder_test_diagnostic(const struct mt6797_a72_binder *binder,
				   struct mt6797_a72_binder_diagnostic *snapshot)
{
	mt6797_a72_binder_fill_diagnostic(binder, snapshot);
}
'''
    text = replace_once(text, test_init, test_diagnostic, "KUnit diagnostic helper")
    path.write_text(text, encoding="utf-8")


def apply_controller(root: Path) -> None:
    path = root / CONTROLLER
    text = path.read_text(encoding="utf-8")
    variables = r'''	struct mt6797_a72_admission_controller *controller = dev_get_drvdata(dev);
	bool complete;
	bool consumed;
	const char *trigger_state;
	ssize_t len;
'''
    new_variables = r'''	struct mt6797_a72_admission_controller *controller = dev_get_drvdata(dev);
	struct mt6797_a72_binder_diagnostic diagnostic;
	bool complete;
	bool consumed;
	const char *trigger_state;
	int diagnostic_ret;
	ssize_t len;
'''
    text = replace_once(text, variables, new_variables, "status variables")
    state_anchor = r'''	else
		trigger_state = "terminal";
	len = sysfs_emit(buf, "%s state=%s ",
'''
    state_updated = r'''	else
		trigger_state = "terminal";
	diagnostic_ret = mt6797_a72_binder_diagnostic_snapshot(&diagnostic);
	len = sysfs_emit(buf, "%s state=%s ",
'''
    text = replace_once(text, state_anchor, state_updated, "status snapshot call")
    tail = r'''	len += sysfs_emit_at(buf, len,
			     "cpu_requests=%u cpu9_requests=0 ",
			     READ_ONCE(controller->state.cpu_requests));
	return len + sysfs_emit_at(buf, len,
				   "cpu_off_requests=0 retries=0\n");
'''
    extended = r'''	len += sysfs_emit_at(buf, len,
			     "cpu_requests=%u cpu9_requests=0 ",
			     READ_ONCE(controller->state.cpu_requests));
	len += sysfs_emit_at(buf, len, "cpu_off_requests=0 retries=0 ");
	len += sysfs_emit_at(buf, len, "binder_snapshot_ret=%d binder_abi=%u ",
			     diagnostic_ret, diagnostic.abi);
	len += sysfs_emit_at(buf, len, "lifecycle=%u terminal=%u last_stage=%u ",
			     diagnostic.lifecycle, diagnostic.terminal,
			     diagnostic.last_stage);
	len += sysfs_emit_at(buf, len, "stage_errno=%d rollback_errno=%d ",
			     diagnostic.stage_errno, diagnostic.rollback_errno);
	len += sysfs_emit_at(buf, len, "checkpoint_errno=%d attempted=%u ",
			     diagnostic.checkpoint_errno, diagnostic.attempted);
	len += sysfs_emit_at(buf, len, "watchdog_armed=%u p27_owned=%u ",
			     diagnostic.watchdog_armed, diagnostic.p27_owned);
	len += sysfs_emit_at(buf, len, "rollback_mask=0x%x retained_mask=0x%x ",
			     diagnostic.rollback_mask, diagnostic.retained_mask);
	len += sysfs_emit_at(buf, len, "p27a_op=%u p27a_error=%d ",
			     diagnostic.p27_acquire_operation,
			     diagnostic.p27_acquire_error);
	len += sysfs_emit_at(buf, len, "p27a_attempted=0x%x p27a_completed=0x%x ",
			     diagnostic.p27_acquire_attempted,
			     diagnostic.p27_acquire_completed);
	len += sysfs_emit_at(buf, len, "p27a_spm_before=0x%x p27a_spm_after=0x%x ",
			     diagnostic.p27_acquire_spm_before,
			     diagnostic.p27_acquire_spm_after);
	len += sysfs_emit_at(buf, len, "p27a_bpll=0x%x p27a_owned=%u p27a_sealed=%u ",
			     diagnostic.p27_acquire_bpll,
			     diagnostic.p27_acquire_owned,
			     diagnostic.p27_acquire_sealed);
	len += sysfs_emit_at(buf, len, "p27r_op=%u p27r_error=%d ",
			     diagnostic.p27_release_operation,
			     diagnostic.p27_release_error);
	len += sysfs_emit_at(buf, len, "p27r_attempted=0x%x p27r_completed=0x%x ",
			     diagnostic.p27_release_attempted,
			     diagnostic.p27_release_completed);
	len += sysfs_emit_at(buf, len, "p27r_spm_before=0x%x p27r_spm_after=0x%x ",
			     diagnostic.p27_release_spm_before,
			     diagnostic.p27_release_spm_after);
	return len + sysfs_emit_at(buf, len,
				   "p27r_bpll=0x%x p27r_owned=%u p27r_sealed=%u\n",
				   diagnostic.p27_release_bpll,
				   diagnostic.p27_release_owned,
				   diagnostic.p27_release_sealed);
'''
    text = replace_once(text, tail, extended, "status diagnostic fields")
    path.write_text(text, encoding="utf-8")


def apply_test(root: Path) -> None:
    path = root / BINDER_TEST
    text = path.read_text(encoding="utf-8")
    anchor = r'''static void mt6797_binder_one_shot_test(struct kunit *test)
'''
    test = r'''static void mt6797_binder_p27_diagnostic_test(struct kunit *test)
{
	struct mt6797_binder_test_state *state = test->priv;
	struct mt6797_a72_binder_diagnostic diagnostic;
	u32 acquire_mask = MT6797_A72_EFFECT_P27_RESET_RELEASED |
		MT6797_A72_EFFECT_BPLL_ORDER_READ |
		MT6797_A72_EFFECT_PWRAP_ASSERTED;
	u32 release_mask = acquire_mask | MT6797_A72_EFFECT_PWRAP_DEASSERTED |
		MT6797_A72_EFFECT_P27_RESET_RESTORED;
	int ret;

	state->malformed = TEST_MALFORMED_P27;
	ret = mt6797_a72_binder_test_boot(&state->binder, 8,
					 mt6797_binder_test_cpu_boot);
	KUNIT_ASSERT_EQ(test, ret, -EPROTO);
	mt6797_a72_binder_test_diagnostic(&state->binder, &diagnostic);
	KUNIT_EXPECT_EQ(test, diagnostic.abi,
			MT6797_A72_BINDER_DIAGNOSTIC_ABI);
	KUNIT_EXPECT_EQ(test, diagnostic.lifecycle,
			(u32)MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL);
	KUNIT_EXPECT_EQ(test, diagnostic.terminal,
			(u32)MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO);
	KUNIT_EXPECT_EQ(test, diagnostic.last_stage,
			(u32)MT6797_A72_TRANSITION_STAGE_P27);
	KUNIT_EXPECT_EQ(test, diagnostic.stage_errno, -EPROTO);
	KUNIT_EXPECT_EQ(test, diagnostic.rollback_errno, -EPROTO);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_operation,
			(u32)MT6797_A72_PLATFORM_EFFECT_P27_ACQUIRE);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_attempted, acquire_mask);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_completed, acquire_mask);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_owned, 1U);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_sealed, 0U);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_release_operation,
			(u32)MT6797_A72_PLATFORM_EFFECT_P27_RELEASE);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_release_error, 0);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_release_attempted, release_mask);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_release_completed, release_mask);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_release_owned, 0U);
	KUNIT_EXPECT_EQ(test, diagnostic.p27_release_sealed, 1U);
}

static void mt6797_binder_one_shot_test(struct kunit *test)
'''
    text = replace_once(text, anchor, test, "P27 diagnostic KUnit case")
    cases = r'''	KUNIT_CASE(mt6797_binder_malformed_owners_test),
	KUNIT_CASE(mt6797_binder_one_shot_test),
'''
    updated = r'''	KUNIT_CASE(mt6797_binder_malformed_owners_test),
	KUNIT_CASE(mt6797_binder_p27_diagnostic_test),
	KUNIT_CASE(mt6797_binder_one_shot_test),
'''
    text = replace_once(text, cases, updated, "P27 diagnostic case registration")
    path.write_text(text, encoding="utf-8")


def apply(root: Path) -> None:
    apply_header(root)
    apply_internal(root)
    apply_binder(root)
    apply_controller(root)
    apply_test(root)
