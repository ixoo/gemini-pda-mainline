// SPDX-License-Identifier: GPL-2.0-only
/*
 * One-way handoff receiver for stopped MT6797 DVFSP firmware
 *
 * Copyright (c) 2026 Julien Etienne
 */

#include <linux/bitops.h>
#include <linux/clk.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/devm-helpers.h>
#include <linux/io.h>
#include <linux/jiffies.h>
#include <linux/mfd/syscon.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>
#include <linux/workqueue.h>

#define CSPM_PCM_CON0			0x018
#define CSPM_PCM_CON1			0x01c
#define CSPM_PCM_PWR_IO_EN		0x02c
#define CSPM_PCM_REG15_DATA		0x13c
#define CSPM_PCM_TIMER_OUT		0x150
#define CSPM_PCM_FSM_STA		0x178
#define CSPM_SW_RSV0			0x608

#define INFRACFG_INFRA2_PDN_STA		0x0b0

#define PCM_CON0_PCM_KICK		BIT(0)
#define PCM_CON0_IM_KICK		BIT(1)
#define PCM_CON0_PCM_SW_RESET		BIT(15)
#define PCM_CON0_ACTIVITY_MASK		(PCM_CON0_PCM_KICK | \
					 PCM_CON0_IM_KICK | \
					 PCM_CON0_PCM_SW_RESET)
#define PCM_CON1_TIMER_EN		BIT(5)
#define PCM_CON1_WDT_EN			BIT(8)
#define PCM_CON1_ACTIVITY_MASK		(PCM_CON1_TIMER_EN | PCM_CON1_WDT_EN)
#define PCM_CON1_AN_STOPPED		0x00006c00
#define PCM_FSM_STA_RESET		0x00048490
#define PCM_SW_RSV_AN_STOPPED		0xbabebabe
#define INFRA_I2C_APPM_GATED		BIT(1)

#define MT6797_DVFSP_SAMPLE_COUNT	6
#define MT6797_DVFSP_SW_RSV_COUNT	7
#define MT6797_DVFSP_LATE_DELAY_MS	45000

enum mt6797_dvfsp_sample_id {
	MT6797_DVFSP_PRE0,
	MT6797_DVFSP_PRE1,
	MT6797_DVFSP_PRE2,
	MT6797_DVFSP_ENABLED,
	MT6797_DVFSP_POST,
	MT6797_DVFSP_LATE,
};

enum mt6797_dvfsp_handoff_state {
	MT6797_DVFSP_UNCLAIMED,
	MT6797_DVFSP_VALIDATING,
	MT6797_DVFSP_NORMALIZING,
	MT6797_DVFSP_PROVISIONAL,
	MT6797_DVFSP_READY,
	MT6797_DVFSP_INCONCLUSIVE,
	MT6797_DVFSP_FAULTED,
};

enum mt6797_dvfsp_late_state {
	MT6797_DVFSP_LATE_NOT_SCHEDULED,
	MT6797_DVFSP_LATE_PENDING,
	MT6797_DVFSP_LATE_PASSED,
	MT6797_DVFSP_LATE_FAILED,
};

enum mt6797_dvfsp_initial_gate {
	MT6797_DVFSP_GATE_UNKNOWN,
	MT6797_DVFSP_GATE_UNGATED,
	MT6797_DVFSP_GATE_GATED,
};

struct mt6797_dvfsp_snapshot {
	u32 timer_before;
	u32 pcm_con0;
	u32 pcm_con1;
	u32 pcm_pwr_io_en;
	u32 pcm_reg15_data;
	u32 pcm_fsm_sta;
	u32 sw_rsv[MT6797_DVFSP_SW_RSV_COUNT];
	u32 infra2_pdn_sta;
	u32 timer_after;
	bool infra2_pdn_sta_valid;
};

struct mt6797_dvfsp_handoff {
	struct device *dev;
	void __iomem *cspm;
	struct regmap *infracfg;
	struct clk *i2c_clk;
	/* Protects state, samples, counters, and late-work transitions. */
	struct mutex lock;
	struct delayed_work late_work;
	struct mt6797_dvfsp_snapshot samples[MT6797_DVFSP_SAMPLE_COUNT];
	bool sample_valid[MT6797_DVFSP_SAMPLE_COUNT];
	enum mt6797_dvfsp_handoff_state state;
	enum mt6797_dvfsp_late_state late_state;
	enum mt6797_dvfsp_initial_gate initial_gate;
	const char *reason;
	unsigned int transition_attempts;
	unsigned int enable_successes;
	unsigned int disable_count;
	unsigned int late_checks;
	unsigned int fault_count;
};

static const char * const mt6797_dvfsp_sample_names[] = {
	[MT6797_DVFSP_PRE0] = "pre0",
	[MT6797_DVFSP_PRE1] = "pre1",
	[MT6797_DVFSP_PRE2] = "pre2",
	[MT6797_DVFSP_ENABLED] = "enabled",
	[MT6797_DVFSP_POST] = "post",
	[MT6797_DVFSP_LATE] = "late",
};

static const char * const mt6797_dvfsp_state_names[] = {
	[MT6797_DVFSP_UNCLAIMED] = "unclaimed",
	[MT6797_DVFSP_VALIDATING] = "validating",
	[MT6797_DVFSP_NORMALIZING] = "normalizing",
	[MT6797_DVFSP_PROVISIONAL] = "provisional",
	[MT6797_DVFSP_READY] = "ready",
	[MT6797_DVFSP_INCONCLUSIVE] = "inconclusive",
	[MT6797_DVFSP_FAULTED] = "faulted",
};

static const char * const mt6797_dvfsp_late_names[] = {
	[MT6797_DVFSP_LATE_NOT_SCHEDULED] = "not-scheduled",
	[MT6797_DVFSP_LATE_PENDING] = "pending",
	[MT6797_DVFSP_LATE_PASSED] = "passed",
	[MT6797_DVFSP_LATE_FAILED] = "failed",
};

static const char * const mt6797_dvfsp_gate_names[] = {
	[MT6797_DVFSP_GATE_UNKNOWN] = "unknown",
	[MT6797_DVFSP_GATE_UNGATED] = "ungated",
	[MT6797_DVFSP_GATE_GATED] = "gated",
};

static void
mt6797_dvfsp_take_snapshot(struct mt6797_dvfsp_handoff *handoff,
			   enum mt6797_dvfsp_sample_id id)
{
	struct mt6797_dvfsp_snapshot *snapshot = &handoff->samples[id];
	unsigned int value;
	int i;

	snapshot->timer_before =
		readl(handoff->cspm + CSPM_PCM_TIMER_OUT);
	snapshot->pcm_con0 = readl(handoff->cspm + CSPM_PCM_CON0);
	snapshot->pcm_con1 = readl(handoff->cspm + CSPM_PCM_CON1);
	snapshot->pcm_pwr_io_en =
		readl(handoff->cspm + CSPM_PCM_PWR_IO_EN);
	snapshot->pcm_reg15_data =
		readl(handoff->cspm + CSPM_PCM_REG15_DATA);
	snapshot->pcm_fsm_sta =
		readl(handoff->cspm + CSPM_PCM_FSM_STA);

	for (i = 0; i < MT6797_DVFSP_SW_RSV_COUNT; i++)
		snapshot->sw_rsv[i] =
			readl(handoff->cspm + CSPM_SW_RSV0 + i * sizeof(u32));

	if (!regmap_read(handoff->infracfg, INFRACFG_INFRA2_PDN_STA,
			 &value)) {
		snapshot->infra2_pdn_sta = value;
		snapshot->infra2_pdn_sta_valid = true;
	}

	snapshot->timer_after =
		readl(handoff->cspm + CSPM_PCM_TIMER_OUT);
	handoff->sample_valid[id] = true;

	dev_info(handoff->dev,
		 "sample=%s timer=%08x/%08x con0=%08x con1=%08x "
		 "pwr_io=%08x r15=%08x fsm=%08x "
		 "rsv=%08x,%08x,%08x,%08x,%08x,%08x,%08x "
		 "gate_valid=%u gate=%08x\n",
		 mt6797_dvfsp_sample_names[id],
		 snapshot->timer_before, snapshot->timer_after,
		 snapshot->pcm_con0, snapshot->pcm_con1,
		 snapshot->pcm_pwr_io_en, snapshot->pcm_reg15_data,
		 snapshot->pcm_fsm_sta,
		 snapshot->sw_rsv[0], snapshot->sw_rsv[1],
		 snapshot->sw_rsv[2], snapshot->sw_rsv[3],
		 snapshot->sw_rsv[4], snapshot->sw_rsv[5],
		 snapshot->sw_rsv[6],
		 snapshot->infra2_pdn_sta_valid,
		 snapshot->infra2_pdn_sta);
}

static bool
mt6797_dvfsp_snapshot_matches_an(const struct mt6797_dvfsp_snapshot *snapshot)
{
	int i;

	if (snapshot->pcm_con0 & PCM_CON0_ACTIVITY_MASK ||
	    snapshot->pcm_con1 != PCM_CON1_AN_STOPPED ||
	    snapshot->pcm_con1 & PCM_CON1_ACTIVITY_MASK ||
	    snapshot->pcm_pwr_io_en != 0 ||
	    snapshot->pcm_reg15_data != 0 ||
	    snapshot->pcm_fsm_sta != PCM_FSM_STA_RESET ||
	    snapshot->timer_before != 0 ||
	    snapshot->timer_after != 0)
		return false;

	for (i = 0; i < MT6797_DVFSP_SW_RSV_COUNT; i++)
		if (snapshot->sw_rsv[i] != PCM_SW_RSV_AN_STOPPED)
			return false;

	return true;
}

static bool
mt6797_dvfsp_pcm_equal(const struct mt6797_dvfsp_snapshot *left,
		       const struct mt6797_dvfsp_snapshot *right)
{
	int i;

	if (left->timer_before != right->timer_before ||
	    left->timer_after != right->timer_after ||
	    left->pcm_con0 != right->pcm_con0 ||
	    left->pcm_con1 != right->pcm_con1 ||
	    left->pcm_pwr_io_en != right->pcm_pwr_io_en ||
	    left->pcm_reg15_data != right->pcm_reg15_data ||
	    left->pcm_fsm_sta != right->pcm_fsm_sta)
		return false;

	for (i = 0; i < MT6797_DVFSP_SW_RSV_COUNT; i++)
		if (left->sw_rsv[i] != right->sw_rsv[i])
			return false;

	return true;
}

static bool
mt6797_dvfsp_gate_is(const struct mt6797_dvfsp_snapshot *snapshot,
		     bool gated)
{
	if (!snapshot->infra2_pdn_sta_valid)
		return false;

	return !!(snapshot->infra2_pdn_sta & INFRA_I2C_APPM_GATED) == gated;
}

static bool
mt6797_dvfsp_pre_signature_stable(struct mt6797_dvfsp_handoff *handoff)
{
	const struct mt6797_dvfsp_snapshot *baseline =
		&handoff->samples[MT6797_DVFSP_PRE0];
	int i;

	for (i = MT6797_DVFSP_PRE0; i <= MT6797_DVFSP_PRE2; i++) {
		if (!mt6797_dvfsp_snapshot_matches_an(&handoff->samples[i]))
			return false;
		if (!mt6797_dvfsp_pcm_equal(baseline, &handoff->samples[i]))
			return false;
	}

	return true;
}

static enum mt6797_dvfsp_initial_gate
mt6797_dvfsp_classify_initial_gate(struct mt6797_dvfsp_handoff *handoff)
{
	bool gated;
	int i;

	for (i = MT6797_DVFSP_PRE0; i <= MT6797_DVFSP_PRE2; i++)
		if (!handoff->samples[i].infra2_pdn_sta_valid)
			return MT6797_DVFSP_GATE_UNKNOWN;

	gated = !!(handoff->samples[MT6797_DVFSP_PRE0].infra2_pdn_sta &
		   INFRA_I2C_APPM_GATED);
	for (i = MT6797_DVFSP_PRE1; i <= MT6797_DVFSP_PRE2; i++)
		if (!!(handoff->samples[i].infra2_pdn_sta &
		       INFRA_I2C_APPM_GATED) != gated)
			return MT6797_DVFSP_GATE_UNKNOWN;

	return gated ? MT6797_DVFSP_GATE_GATED :
		       MT6797_DVFSP_GATE_UNGATED;
}

static void
mt6797_dvfsp_fault_locked(struct mt6797_dvfsp_handoff *handoff,
			  const char *reason)
{
	if (handoff->state == MT6797_DVFSP_FAULTED)
		return;

	handoff->state = MT6797_DVFSP_FAULTED;
	handoff->reason = reason;
	handoff->fault_count++;
	dev_err(handoff->dev,
		"state=faulted reason=%s i2c6_policy=disabled\n", reason);
}

static void mt6797_dvfsp_late_work(struct work_struct *work)
{
	struct mt6797_dvfsp_handoff *handoff =
		container_of(to_delayed_work(work),
			     struct mt6797_dvfsp_handoff, late_work);
	const struct mt6797_dvfsp_snapshot *baseline =
		&handoff->samples[MT6797_DVFSP_PRE0];
	const struct mt6797_dvfsp_snapshot *late =
		&handoff->samples[MT6797_DVFSP_LATE];

	mutex_lock(&handoff->lock);
	if (handoff->state != MT6797_DVFSP_PROVISIONAL ||
	    handoff->late_state != MT6797_DVFSP_LATE_PENDING)
		goto unlock;

	handoff->late_checks++;
	mt6797_dvfsp_take_snapshot(handoff, MT6797_DVFSP_LATE);
	if (!mt6797_dvfsp_snapshot_matches_an(late) ||
	    !mt6797_dvfsp_pcm_equal(baseline, late) ||
	    !mt6797_dvfsp_gate_is(late, true)) {
		handoff->late_state = MT6797_DVFSP_LATE_FAILED;
		mt6797_dvfsp_fault_locked(handoff, "late-revalidation-failed");
		goto unlock;
	}

	handoff->state = MT6797_DVFSP_READY;
	handoff->late_state = MT6797_DVFSP_LATE_PASSED;
	handoff->reason = "late-validation-passed";
	dev_info(handoff->dev,
		 "state=ready normalization=ungated-to-gated "
		 "late_validation=passed i2c6_policy=disabled\n");

unlock:
	mutex_unlock(&handoff->lock);
}

static void mt6797_dvfsp_run_handoff(struct mt6797_dvfsp_handoff *handoff)
{
	const struct mt6797_dvfsp_snapshot *baseline =
		&handoff->samples[MT6797_DVFSP_PRE0];
	const struct mt6797_dvfsp_snapshot *enabled =
		&handoff->samples[MT6797_DVFSP_ENABLED];
	const struct mt6797_dvfsp_snapshot *post =
		&handoff->samples[MT6797_DVFSP_POST];
	const char *failure = NULL;
	int ret;

	mutex_lock(&handoff->lock);
	handoff->state = MT6797_DVFSP_VALIDATING;
	handoff->reason = "initial-validation";
	dev_info(handoff->dev,
		 "state=validating operation=one-way-handoff i2c6_policy=disabled\n");

	mt6797_dvfsp_take_snapshot(handoff, MT6797_DVFSP_PRE0);
	usleep_range(2000, 2500);
	mt6797_dvfsp_take_snapshot(handoff, MT6797_DVFSP_PRE1);
	usleep_range(18000, 19000);
	mt6797_dvfsp_take_snapshot(handoff, MT6797_DVFSP_PRE2);

	if (!mt6797_dvfsp_pre_signature_stable(handoff)) {
		mt6797_dvfsp_fault_locked(handoff, "initial-signature-mismatch");
		goto unlock;
	}

	handoff->initial_gate = mt6797_dvfsp_classify_initial_gate(handoff);
	if (handoff->initial_gate == MT6797_DVFSP_GATE_UNKNOWN) {
		mt6797_dvfsp_fault_locked(handoff, "initial-gate-invalid-or-changed");
		goto unlock;
	}

	if (handoff->initial_gate == MT6797_DVFSP_GATE_GATED) {
		handoff->state = MT6797_DVFSP_INCONCLUSIVE;
		handoff->reason = "initial-gate-already-gated";
		dev_warn(handoff->dev,
			 "state=inconclusive "
			 "reason=initial-gate-already-gated "
			 "transition_attempts=0 i2c6_policy=disabled\n");
		goto unlock;
	}

	handoff->state = MT6797_DVFSP_NORMALIZING;
	handoff->reason = "ccf-balance-in-progress";
	handoff->transition_attempts++;
	dev_info(handoff->dev,
		 "state=normalizing transition=ccf-temporary-reference attempt=1\n");

	ret = clk_prepare_enable(handoff->i2c_clk);
	if (ret) {
		mt6797_dvfsp_fault_locked(handoff, "ccf-enable-failed");
		goto unlock;
	}
	handoff->enable_successes++;

	mt6797_dvfsp_take_snapshot(handoff, MT6797_DVFSP_ENABLED);
	if (!mt6797_dvfsp_snapshot_matches_an(enabled) ||
	    !mt6797_dvfsp_pcm_equal(baseline, enabled))
		failure = "pcm-changed-while-clock-held";
	else if (!mt6797_dvfsp_gate_is(enabled, false))
		failure = "clock-not-ungated-while-held";

	clk_disable_unprepare(handoff->i2c_clk);
	handoff->disable_count++;
	mt6797_dvfsp_take_snapshot(handoff, MT6797_DVFSP_POST);

	if (!failure &&
	    (!mt6797_dvfsp_snapshot_matches_an(post) ||
	     !mt6797_dvfsp_pcm_equal(baseline, post)))
		failure = "pcm-changed-after-clock-balance";
	if (!failure && !mt6797_dvfsp_gate_is(post, true))
		failure = "clock-remained-ungated-after-balance";

	if (failure) {
		mt6797_dvfsp_fault_locked(handoff, failure);
		goto unlock;
	}

	handoff->state = MT6797_DVFSP_PROVISIONAL;
	handoff->late_state = MT6797_DVFSP_LATE_PENDING;
	handoff->reason = "normalization-complete-late-pending";
	if (!schedule_delayed_work(&handoff->late_work,
				   msecs_to_jiffies(MT6797_DVFSP_LATE_DELAY_MS))) {
		handoff->late_state = MT6797_DVFSP_LATE_NOT_SCHEDULED;
		mt6797_dvfsp_fault_locked(handoff, "late-validation-not-scheduled");
		goto unlock;
	}

	dev_info(handoff->dev,
		 "state=provisional normalization=ungated-to-gated "
		 "enable_successes=1 disable_count=1 "
		 "late_validation=pending delay_ms=%u "
		 "i2c6_policy=disabled\n",
		 MT6797_DVFSP_LATE_DELAY_MS);

unlock:
	mutex_unlock(&handoff->lock);
}

static ssize_t state_show(struct device *dev, struct device_attribute *attr,
			  char *buf)
{
	struct mt6797_dvfsp_handoff *handoff = dev_get_drvdata(dev);
	ssize_t length;

	mutex_lock(&handoff->lock);
	length = sysfs_emit(buf, "%s\n",
			    mt6797_dvfsp_state_names[handoff->state]);
	mutex_unlock(&handoff->lock);

	return length;
}
static DEVICE_ATTR_RO(state);

static ssize_t status_show(struct device *dev, struct device_attribute *attr,
			   char *buf)
{
	struct mt6797_dvfsp_handoff *handoff = dev_get_drvdata(dev);
	ssize_t length;

	mutex_lock(&handoff->lock);
	length = sysfs_emit(buf,
			    "state=%s reason=%s initial_gate=%s "
			    "transition_attempts=%u enable_successes=%u "
			    "disable_count=%u late=%s late_checks=%u faults=%u "
			    "i2c6_policy=disabled\n",
			    mt6797_dvfsp_state_names[handoff->state],
			    handoff->reason,
			    mt6797_dvfsp_gate_names[handoff->initial_gate],
			    handoff->transition_attempts,
			    handoff->enable_successes, handoff->disable_count,
			    mt6797_dvfsp_late_names[handoff->late_state],
			    handoff->late_checks, handoff->fault_count);
	mutex_unlock(&handoff->lock);

	return length;
}
static DEVICE_ATTR_RO(status);

static ssize_t snapshots_show(struct device *dev,
			      struct device_attribute *attr, char *buf)
{
	struct mt6797_dvfsp_handoff *handoff = dev_get_drvdata(dev);
	ssize_t length = 0;
	int i;

	mutex_lock(&handoff->lock);
	for (i = 0; i < MT6797_DVFSP_SAMPLE_COUNT; i++) {
		const struct mt6797_dvfsp_snapshot *snapshot =
			&handoff->samples[i];

		if (!handoff->sample_valid[i])
			continue;

		length += sysfs_emit_at(buf, length,
			"sample=%s timer=%08x/%08x "
			"con0=%08x con1=%08x pwr_io=%08x "
			"r15=%08x fsm=%08x "
			"rsv=%08x,%08x,%08x,%08x,%08x,%08x,%08x "
			"gate_valid=%u gate=%08x\n",
			mt6797_dvfsp_sample_names[i],
			snapshot->timer_before, snapshot->timer_after,
			snapshot->pcm_con0, snapshot->pcm_con1,
			snapshot->pcm_pwr_io_en, snapshot->pcm_reg15_data,
			snapshot->pcm_fsm_sta,
			snapshot->sw_rsv[0], snapshot->sw_rsv[1],
			snapshot->sw_rsv[2], snapshot->sw_rsv[3],
			snapshot->sw_rsv[4], snapshot->sw_rsv[5],
			snapshot->sw_rsv[6],
			snapshot->infra2_pdn_sta_valid,
			snapshot->infra2_pdn_sta);
	}
	mutex_unlock(&handoff->lock);

	return length;
}
static DEVICE_ATTR_RO(snapshots);

static struct attribute *mt6797_dvfsp_handoff_attrs[] = {
	&dev_attr_state.attr,
	&dev_attr_status.attr,
	&dev_attr_snapshots.attr,
	NULL,
};

static const struct attribute_group mt6797_dvfsp_handoff_group = {
	.attrs = mt6797_dvfsp_handoff_attrs,
};

static int mt6797_dvfsp_handoff_probe(struct platform_device *pdev)
{
	struct mt6797_dvfsp_handoff *handoff;
	int ret;

	handoff = devm_kzalloc(&pdev->dev, sizeof(*handoff), GFP_KERNEL);
	if (!handoff)
		return -ENOMEM;

	handoff->dev = &pdev->dev;
	handoff->state = MT6797_DVFSP_UNCLAIMED;
	handoff->late_state = MT6797_DVFSP_LATE_NOT_SCHEDULED;
	handoff->initial_gate = MT6797_DVFSP_GATE_UNKNOWN;
	handoff->reason = "resources-not-ready";
	mutex_init(&handoff->lock);

	handoff->i2c_clk = devm_clk_get(&pdev->dev, "i2c");
	if (IS_ERR(handoff->i2c_clk))
		return dev_err_probe(&pdev->dev, PTR_ERR(handoff->i2c_clk),
				     "cannot acquire I2C_APPM clock\n");

	handoff->infracfg =
		syscon_regmap_lookup_by_phandle(pdev->dev.of_node,
						"mediatek,infracfg");
	if (IS_ERR(handoff->infracfg))
		return dev_err_probe(&pdev->dev, PTR_ERR(handoff->infracfg),
				     "cannot resolve infracfg syscon\n");

	handoff->cspm = devm_platform_ioremap_resource(pdev, 0);
	if (IS_ERR(handoff->cspm))
		return dev_err_probe(&pdev->dev, PTR_ERR(handoff->cspm),
				     "cannot map CSPM validation window\n");

	ret = devm_delayed_work_autocancel(&pdev->dev, &handoff->late_work,
					   mt6797_dvfsp_late_work);
	if (ret)
		return dev_err_probe(&pdev->dev, ret,
				     "cannot allocate late validation work\n");

	platform_set_drvdata(pdev, handoff);
	ret = devm_device_add_group(&pdev->dev, &mt6797_dvfsp_handoff_group);
	if (ret)
		return dev_err_probe(&pdev->dev, ret,
				     "cannot publish read-only handoff state\n");

	mt6797_dvfsp_run_handoff(handoff);
	return 0;
}

static const struct of_device_id mt6797_dvfsp_handoff_of_match[] = {
	{ .compatible = "mediatek,mt6797-dvfsp-handoff" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_dvfsp_handoff_of_match);

static struct platform_driver mt6797_dvfsp_handoff_driver = {
	.probe = mt6797_dvfsp_handoff_probe,
	.driver = {
		.name = "mt6797-dvfsp-handoff",
		.of_match_table = mt6797_dvfsp_handoff_of_match,
		.suppress_bind_attrs = true,
	},
};
builtin_platform_driver(mt6797_dvfsp_handoff_driver);

MODULE_DESCRIPTION("MediaTek MT6797 stopped DVFSP one-way handoff");
MODULE_LICENSE("GPL");
