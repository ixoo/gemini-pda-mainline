/* SPDX-License-Identifier: GPL-2.0-only */
/* Caller owns the bound charger's existing read; no additional transaction. */
int gemini_reg06_transfer(struct i2c_adapter *adap, struct i2c_msg *msgs,
			 struct gemini_reg06_record *record)
{
	struct mt_i2c *i2c;
	int ret;

	if (adap->algo != &mt_i2c_algorithm || adap->nr != 0 ||
	    msgs[0].addr != 0x6b || msgs[1].addr != 0x6b ||
	    msgs[0].flags || msgs[1].flags != I2C_M_RD ||
	    msgs[0].len != 1 || msgs[1].len != 1 ||
	    !msgs[0].buf || !msgs[1].buf || msgs[0].buf[0] != 6)
		return i2c_transfer(adap, msgs, 2);

	i2c_lock_adapter(adap);
	i2c = i2c_get_adapdata(adap);
	i2c->reg06_request = msgs;
	i2c->reg06_pending = record;
	ret = __i2c_transfer(adap, msgs, 2);
	i2c->reg06_pending = NULL;
	i2c->reg06_request = NULL;
	i2c_unlock_adapter(adap);
	return ret;
}
EXPORT_SYMBOL_GPL(gemini_reg06_transfer);
