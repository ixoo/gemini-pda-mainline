/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _GEMINI_REG06_OBSERVER_H
#define _GEMINI_REG06_OBSERVER_H

#include <linux/types.h>

#ifdef CONFIG_MTK_I2C_EXTENSION
#error "Gemini REG06 observer requires native I2C messages"
#endif

struct i2c_adapter;
struct i2c_msg;

struct gemini_reg06_record {
	int master_calls;
	int transfers;
	int result;
	u16 irq;
	u8 fifo_count;
	u8 value;
	bool controller_ok;
	bool fifo_path;
	bool wrrd;
	bool fifo_seen;
};

static inline bool gemini_reg06_valid(const struct gemini_reg06_record *r)
{
	return r->result == 2 && r->master_calls == 1 && r->transfers == 1 &&
		r->controller_ok && r->fifo_path && r->wrrd && r->fifo_seen &&
		r->fifo_count == 1 && (r->irq & 1) && !(r->irq & 6);
}

int gemini_reg06_transfer(struct i2c_adapter *adap, struct i2c_msg *msgs,
			 struct gemini_reg06_record *record);

#endif
