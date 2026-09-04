#if IS_ENABLED(CONFIG_MTK_SOC_THERMAL_OBSERVER)
static u64 mt6797_observer_time_ns(void *context)
{
	return ktime_get_ns();
}

static int mt6797_observer_scan(void *context,
				struct mt6797_thermal_snapshot *snapshot,
				int *aggregate)
{
	return mtk_read_temp_scan(context, aggregate, snapshot);
}

static const struct mt6797_thermal_observer_ops mt6797_observer_ops = {
	.time_ns = mt6797_observer_time_ns,
	.scan = mt6797_observer_scan,
};

static ssize_t mt6797_temperature_snapshot_show(struct device *dev,
					       struct device_attribute *attr,
					       char *buf)
{
	struct mt6797_thermal_snapshot snapshot = {};
	struct mtk_thermal *mt = dev_get_drvdata(dev);
	ssize_t len;
	u32 i;
	int ret;

	ret = mt6797_thermal_observer_capture(&mt->observer, &mt6797_observer_ops,
					     mt, &snapshot);
	/* Return a record even on failure: do not invite error-read retries. */
	len = sysfs_emit(buf,
			"abi=%u attempt=%u error=%d complete=%u count=%u valid_mask=%u winner=%u maximum=%d start_ns=%llu end_ns=%llu\n",
			snapshot.abi, snapshot.attempt, ret, snapshot.complete,
			snapshot.count, snapshot.valid_mask, snapshot.winner,
			snapshot.maximum, snapshot.start_ns, snapshot.end_ns);
	for (i = 0; i < snapshot.count; i++) {
		const struct mt6797_thermal_snapshot_sample *s = &snapshot.samples[i];

		len += sysfs_emit_at(buf, len,
				     "slot=%u bank=%u sensor=%u temperature=%d valid=%u\n",
				     i, s->bank, s->sensor, s->temperature, s->valid);
	}
	return len;
}

static ssize_t mt6797_temperature_snapshot_status_show(struct device *dev,
						      struct device_attribute *attr,
						      char *buf)
{
	struct mtk_thermal *mt = dev_get_drvdata(dev);
	u32 attempts;

	mutex_lock(&mt->observer.lock);
	attempts = mt->observer.budget.attempts;
	mutex_unlock(&mt->observer.lock);
	return sysfs_emit(buf, "abi=%u attempts=%u limit=%u\n",
			  MT6797_THERMAL_SNAPSHOT_ABI, attempts,
			  MT6797_THERMAL_SNAPSHOT_ATTEMPTS);
}

static DEVICE_ATTR(mt6797_temperature_snapshot, 0400,
		   mt6797_temperature_snapshot_show, NULL);
static DEVICE_ATTR(mt6797_temperature_snapshot_status, 0400,
		   mt6797_temperature_snapshot_status_show, NULL);

static struct attribute *mt6797_observer_attrs[] = {
	&dev_attr_mt6797_temperature_snapshot.attr,
	&dev_attr_mt6797_temperature_snapshot_status.attr,
	NULL,
};
ATTRIBUTE_GROUPS(mt6797_observer);
#endif
