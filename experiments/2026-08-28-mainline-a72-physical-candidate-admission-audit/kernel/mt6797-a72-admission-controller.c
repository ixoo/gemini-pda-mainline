// SPDX-License-Identifier: GPL-2.0-only
/* Candidate-only one-shot MT6797 CPU8 admission controller. */

#include <asm/late_cpu_profile.h>
#include <asm/mt6797_a72_membership.h>

#include <linux/atomic.h>
#include <linux/cpu.h>
#include <linux/device.h>
#include <linux/errno.h>
#include <linux/init.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_platform.h>
#include <linux/platform_device.h>
#include <linux/slab.h>
#include <linux/soc/mediatek/mt6797-a72-binder.h>
#include <linux/string.h>

#include "mt6797-a72-admission-controller-internal.h"
#include "mt6797-a72-physical-source-observer-internal.h"

#define MT6797_A72_ADMISSION_TAG "GEMINI_A72_ADMISSION_V1"
#define MT6797_A72_ADMISSION_CPU 8

struct mt6797_a72_admission_controller {
	struct device *binder;
	struct mt6797_a72_physical_source_context source;
	struct mt6797_a72_admission_controller_state state;
};

static bool
mt6797_a72_admission_ops_valid(const struct mt6797_a72_admission_controller_ops *ops)
{
	return ops && ops->binder_ready && ops->ready_token &&
		ops->source_register && ops->source_unregister &&
		ops->derive_cpu8 && ops->publish_up && ops->add_cpu;
}

void
mt6797_a72_admission_state_init(struct mt6797_a72_admission_controller_state *state)
{
	memset(state, 0, sizeof(*state));
	atomic_set(&state->consumed, 0);
}

int
mt6797_a72_admission_run(struct mt6797_a72_admission_controller_state *state,
	const struct mt6797_a72_admission_controller_ops *ops, void *context)
{
	const struct arm64_late_cpu_ready_token *ready;
	bool source_registered = false;
	int ret;

	if (!state || !mt6797_a72_admission_ops_valid(ops))
		return -EINVAL;
	if (atomic_read(&state->consumed))
		return -EALREADY;
	if (!ops->binder_ready(context))
		return -EPROBE_DEFER;
	ready = ops->ready_token(context);
	if (!ready)
		return -EAGAIN;
	if (atomic_cmpxchg(&state->consumed, 0, 1))
		return -EALREADY;

	ret = ops->source_register(context);
	if (ret)
		goto out_terminal;
	source_registered = true;
	ret = ops->derive_cpu8(context, ready, &state->transaction);
	if (ret)
		goto out_unregister;
	ret = ops->publish_up(context, &state->transaction);
	if (ret)
		goto out_unregister;
	state->cpu_requests++;
	ret = ops->add_cpu(context, MT6797_A72_ADMISSION_CPU);

out_unregister:
	if (source_registered)
		ops->source_unregister(context);
out_terminal:
	state->operation_ret = ret;
	return ret;
}

static bool mt6797_a72_admission_binder_ready(void *context)
{
	(void)context;
	return mt6797_a72_binder_available();
}

static const struct arm64_late_cpu_ready_token *
mt6797_a72_admission_ready_token(void *context)
{
	(void)context;
	return arm64_get_late_cpu_ready_token();
}

static int mt6797_a72_admission_source_register(void *context)
{
	struct mt6797_a72_admission_controller *controller = context;

	return mt6797_a72_source_register(&controller->source);
}

static void mt6797_a72_admission_source_unregister(void *context)
{
	struct mt6797_a72_admission_controller *controller = context;

	mt6797_a72_source_unregister(&controller->source);
}

static int
mt6797_a72_admission_derive_cpu8(void *context,
	const struct arm64_late_cpu_ready_token *ready,
	struct mt6797_a72_transaction *transaction)
{
	(void)context;
	return mt6797_a72_membership_derive_cpu8(ready, transaction);
}

static int
mt6797_a72_admission_publish_up(void *context,
	struct mt6797_a72_transaction *transaction)
{
	(void)context;
	return mt6797_a72_membership_publish_up(transaction);
}

static int mt6797_a72_admission_add_cpu(void *context, unsigned int cpu)
{
	(void)context;
	return add_cpu(cpu);
}

static const struct mt6797_a72_admission_controller_ops
mt6797_a72_admission_production_ops = {
	.binder_ready = mt6797_a72_admission_binder_ready,
	.ready_token = mt6797_a72_admission_ready_token,
	.source_register = mt6797_a72_admission_source_register,
	.source_unregister = mt6797_a72_admission_source_unregister,
	.derive_cpu8 = mt6797_a72_admission_derive_cpu8,
	.publish_up = mt6797_a72_admission_publish_up,
	.add_cpu = mt6797_a72_admission_add_cpu,
};

static void mt6797_a72_admission_put_device(void *data)
{
	put_device(data);
}

static int
mt6797_a72_admission_resolve(struct device *dev, const char *property,
			     struct device **supplier)
{
	struct platform_device *pdev;
	struct device_node *node;
	int ret;

	node = of_parse_phandle(dev->of_node, property, 0);
	if (!node)
		return -EINVAL;
	pdev = of_find_device_by_node(node);
	of_node_put(node);
	if (!pdev)
		return -EPROBE_DEFER;
	if (!device_is_bound(&pdev->dev)) {
		put_device(&pdev->dev);
		return -EPROBE_DEFER;
	}
	if (!device_link_add(dev, &pdev->dev, DL_FLAG_AUTOREMOVE_CONSUMER)) {
		put_device(&pdev->dev);
		return -EINVAL;
	}
	ret = devm_add_action_or_reset(dev, mt6797_a72_admission_put_device,
				       &pdev->dev);
	if (ret)
		return ret;
	*supplier = &pdev->dev;
	return 0;
}

static int mt6797_a72_admission_probe(struct platform_device *pdev)
{
	struct mt6797_a72_admission_controller *controller;
	struct device *bigidvfs;
	struct device *platform;
	struct device *clock;
	struct device *dev = &pdev->dev;
	int ret;

	controller = devm_kzalloc(dev, sizeof(*controller), GFP_KERNEL);
	if (!controller)
		return -ENOMEM;
	mt6797_a72_admission_state_init(&controller->state);
	ret = mt6797_a72_admission_resolve(dev, "mediatek,binder",
					   &controller->binder);
	if (ret)
		return dev_err_probe(dev, ret, "binder unavailable\n");
	ret = mt6797_a72_admission_resolve(dev, "mediatek,platform-state",
					   &platform);
	if (ret)
		return dev_err_probe(dev, ret, "platform-state unavailable\n");
	ret = mt6797_a72_admission_resolve(dev, "mediatek,clock-backend",
					   &clock);
	if (ret)
		return dev_err_probe(dev, ret, "clock backend unavailable\n");
	ret = mt6797_a72_admission_resolve(dev, "mediatek,bigidvfs-backend",
					   &bigidvfs);
	if (ret)
		return dev_err_probe(dev, ret, "BigiDVFS backend unavailable\n");
	mt6797_a72_source_context_init(&controller->source, platform, clock,
				       bigidvfs);
	ret = mt6797_a72_admission_run(&controller->state,
				       &mt6797_a72_admission_production_ops,
				       controller);
	if (!atomic_read(&controller->state.consumed))
		return dev_err_probe(dev, ret, "admission prerequisite unavailable\n");

	platform_set_drvdata(pdev, controller);
	dev_info(dev, MT6797_A72_ADMISSION_TAG
		 " state=terminal ret=%d consumed=1 requests=%u/0/0 retries=0\n",
		 ret, controller->state.cpu_requests);
	return 0;
}

static const struct of_device_id mt6797_a72_admission_of_match[] = {
	{ .compatible = "mediatek,mt6797-a72-admission-controller" },
	{ }
};
MODULE_DEVICE_TABLE(of, mt6797_a72_admission_of_match);

static struct platform_driver mt6797_a72_admission_driver = {
	.probe = mt6797_a72_admission_probe,
	.driver = {
		.name = "mt6797-a72-admission-controller",
		.of_match_table = mt6797_a72_admission_of_match,
		.suppress_bind_attrs = true,
	},
};

static int __init mt6797_a72_admission_init(void)
{
	return platform_driver_register(&mt6797_a72_admission_driver);
}
late_initcall(mt6797_a72_admission_init);

MODULE_DESCRIPTION("MT6797 candidate-only one-shot CPU8 admission controller");
MODULE_LICENSE("GPL");
