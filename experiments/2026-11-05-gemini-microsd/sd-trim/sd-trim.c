// SPDX-License-Identifier: GPL-2.0-only
/*
 * Diagnostic only: set the MT6351 VMCH and VMC trim fields to the values the
 * vendor kernel runs the microSD slot with, and put the firmware's values
 * back on unload.
 *
 * The firmware leaves VMCH_CAL (0x0ace[4:0]) at 5 and VMC_CAL (0x0ae2[4:0])
 * at 0x1b. The vendor MSDC1 probe subtracts 5 and 0x1b (modulo 32), so
 * Gemian runs both at 0. Mainline keeps the firmware values.
 *
 * A parameter of -1 leaves that field alone.
 */
#include <linux/module.h>
#include <linux/regmap.h>
#include <linux/regulator/consumer.h>

#define CAL_MASK 0x1f

static int vmch_cal = -1;
module_param(vmch_cal, int, 0444);
static int vmc_cal = -1;
module_param(vmc_cal, int, 0444);

struct trim {
	const char *name;
	unsigned int reg;
	int *want;
	struct regulator *reg_handle;
	struct regmap *map;
	unsigned int saved;
	bool written;
};

static struct trim trims[] = {
	{ "vmch", 0x0ace, &vmch_cal },
	{ "vmc", 0x0ae2, &vmc_cal },
};

static void trim_restore(void)
{
	unsigned int val;
	int i;

	for (i = ARRAY_SIZE(trims) - 1; i >= 0; i--) {
		struct trim *t = &trims[i];

		if (t->written) {
			regmap_update_bits(t->map, t->reg, CAL_MASK, t->saved);
			regmap_read(t->map, t->reg, &val);
			pr_info("sd-trim: %s 0x%04x restored to 0x%04x\n",
				t->name, t->reg, val);
			t->written = false;
		}
		if (!IS_ERR_OR_NULL(t->reg_handle))
			regulator_put(t->reg_handle);
		t->reg_handle = NULL;
	}
}

static int __init sd_trim_init(void)
{
	unsigned int val;
	int i, ret;

	for (i = 0; i < ARRAY_SIZE(trims); i++) {
		struct trim *t = &trims[i];

		if (*t->want < -1 || *t->want > CAL_MASK) {
			ret = -EINVAL;
			goto fail;
		}
		t->reg_handle = regulator_get_optional(NULL, t->name);
		if (IS_ERR(t->reg_handle)) {
			ret = PTR_ERR(t->reg_handle);
			pr_err("sd-trim: no %s regulator: %d\n", t->name, ret);
			goto fail;
		}
		t->map = regulator_get_regmap(t->reg_handle);
		if (IS_ERR(t->map)) {
			ret = PTR_ERR(t->map);
			goto fail;
		}
		ret = regmap_read(t->map, t->reg, &val);
		if (ret)
			goto fail;
		t->saved = val & CAL_MASK;
		pr_info("sd-trim: %s 0x%04x = 0x%04x at %d uV\n", t->name,
			t->reg, val, regulator_get_voltage(t->reg_handle));
	}

	for (i = 0; i < ARRAY_SIZE(trims); i++) {
		struct trim *t = &trims[i];

		if (*t->want < 0)
			continue;
		ret = regmap_update_bits(t->map, t->reg, CAL_MASK, *t->want);
		if (ret)
			goto fail;
		t->written = true;
		regmap_read(t->map, t->reg, &val);
		pr_info("sd-trim: %s 0x%04x set to 0x%04x\n", t->name, t->reg,
			val);
	}
	return 0;

fail:
	trim_restore();
	return ret;
}

static void __exit sd_trim_exit(void)
{
	trim_restore();
}

module_init(sd_trim_init);
module_exit(sd_trim_exit);
MODULE_DESCRIPTION("Diagnostic: MT6351 microSD supply trims as the vendor sets them");
MODULE_LICENSE("GPL");
