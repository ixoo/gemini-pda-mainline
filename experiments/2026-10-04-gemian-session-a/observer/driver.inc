/* SPDX-License-Identifier: GPL-2.0-only */
/* Diagnostic-only; all state is protected by bq25890_i2c_access. */
static bool reg06_observer;
module_param(reg06_observer, bool, 0400);
MODULE_PARM_DESC(reg06_observer, "Allow one passive REG06 observation");

/* 0 idle, 1 armed, 2 consumed/in flight, 3 terminal. No rearm. */
static unsigned int reg06_state;
static struct gemini_reg06_record reg06_record;

static ssize_t reg06_observe_show(struct device *dev,
				  struct device_attribute *attr, char *buf)
{
	struct gemini_reg06_record *r = &reg06_record;
	ssize_t size;

	mutex_lock(&bq25890_i2c_access);
	if (!reg06_observer) {
		size = scnprintf(buf, PAGE_SIZE, "disabled\n");
	} else if (!reg06_state) {
		reg06_state = 1;
		size = scnprintf(buf, PAGE_SIZE, "armed\n");
	} else if (reg06_state != 3) {
		size = scnprintf(buf, PAGE_SIZE, "pending\n");
	} else if (gemini_reg06_valid(r)) {
		size = scnprintf(buf, PAGE_SIZE,
				"ok ret=%d calls=%d transfers=%d irq=%x fifo=%u value=%02x\n",
				r->result, r->master_calls, r->transfers, r->irq,
				r->fifo_count, r->value);
	} else {
		size = scnprintf(buf, PAGE_SIZE,
				"failed ret=%d calls=%d transfers=%d irq=%x fifo_seen=%u fifo=%u controller=%u fifo_path=%u wrrd=%u\n",
				r->result, r->master_calls, r->transfers, r->irq,
				r->fifo_seen, r->fifo_count, r->controller_ok,
				r->fifo_path, r->wrrd);
	}
	mutex_unlock(&bq25890_i2c_access);
	return size;
}

static DEVICE_ATTR(reg06_observe, 0400, reg06_observe_show, NULL);
